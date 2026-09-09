"""FastAPI router for RailOS Field Evidence, Auth, Supervisor Admin, and Verification."""

from __future__ import annotations

import base64
import binascii
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field
from railos_model import (
    EmergencyReport,
    EvidenceItem,
    EvidenceKind,
    EvidenceManifestV1,
    EvidenceRequirement,
    EvidenceStatus,
    GeoSample,
    GeoVerdict,
    ManifestSigner,
    Severity,
    SupervisorAreaAssignment,
    UserRole,
    WorkExecutionStatus,
    WorkStep,
    compute_sha256_bytes,
)

from .auth import (
    AuthDTO,
    CreateSupervisorRequest,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    UpdateSupervisorAreasRequest,
    UserAccount,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    hash_token,
    require_role,
    verify_password,
)
from .storage import MemoryObjectStore, get_object_store
from .verification import EvidenceVerificationService

router = APIRouter(tags=["field-evidence"])
object_store = get_object_store()
verification_service = EvidenceVerificationService(object_store)


# -----------------------------------------------------------------------------
# In-Memory State for Auth, Assignments, Evidence, and Work Steps
# -----------------------------------------------------------------------------
class FieldEvidenceState:
    """Auth/assignment/demo state. Deliberately in-memory (session-scoped, not
    durable): work_steps, evidence_items, and upload_sessions live in the
    Postgres-backed `state` repository from main.py instead (see COLLECTIONS),
    so evidence media metadata survives a process restart the same way tasks
    and possessions do."""

    def __init__(self):
        self.users: dict[str, dict[str, Any]] = {}
        self.refresh_tokens: dict[str, dict[str, Any]] = {}  # token_hash -> token_info
        self.assignments: dict[str, list[str]] = {}  # user_id -> [section_code, ...]
        self.emergency_reports: dict[str, EmergencyReport] = {}  # report_id -> EmergencyReport
        self.idempotency: dict[str, Any] = {}
        self._seed()

    def _seed(self):
        # Default admin account
        admin_pwd_hash = hash_password("Admin@123")
        self.users["admin-01"] = {
            "userId": "admin-01",
            "employeeId": "EMP001",
            "name": "Chief Controller",
            "role": "ADMIN",
            "passwordHash": admin_pwd_hash,
            "email": "controller@railos.gov.in",
            "active": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }

        # Default field supervisor accounts — one per department (ENGG/SNT/TRD),
        # matching railos_model.Department, so /work/assignments/mine scopes each
        # supervisor to their own department's maintenance tasks instead of every
        # department's. All three share the demo password for convenience.
        sup_pwd_hash = hash_password("Field@123")
        corridor_sections = ["SEC_GZB_DER", "SEC_DER_KRJ", "SEC_KRJ_SMQ", "SEC_SMQ_ALJN"]
        self.users["sup-01"] = {
            "userId": "sup-01",
            "employeeId": "EMP901",
            "name": "Rajesh Kumar (SSE/P-Way)",
            "role": "SUPERVISOR",
            "department": "ENGG",
            "passwordHash": sup_pwd_hash,
            "email": "rajesh.kumar@railos.gov.in",
            "active": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        self.assignments["sup-01"] = corridor_sections
        self.users["sup-02"] = {
            "userId": "sup-02",
            "employeeId": "EMP902",
            "name": "Meena Iyer (SSE/Signal)",
            "role": "SUPERVISOR",
            "department": "SNT",
            "passwordHash": sup_pwd_hash,
            "email": "meena.iyer@railos.gov.in",
            "active": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        self.assignments["sup-02"] = corridor_sections
        self.users["sup-03"] = {
            "userId": "sup-03",
            "employeeId": "EMP903",
            "name": "Arjun Nair (SSE/TRD)",
            "role": "SUPERVISOR",
            "department": "TRD",
            "passwordHash": sup_pwd_hash,
            "email": "arjun.nair@railos.gov.in",
            "active": True,
            "createdAt": datetime.now(timezone.utc).isoformat(),
        }
        self.assignments["sup-03"] = corridor_sections
        # Demo work steps for TSK-0001 are seeded by the Postgres-backed
        # `state` repository (see Repository._seed in main.py) so they persist
        # across restarts alongside evidence_items and upload_sessions.


evidence_state = FieldEvidenceState()


def _authorize_evidence(item: EvidenceItem, user: UserAccount) -> None:
    """Keep evidence media and review metadata scoped to its owner or reviewers."""
    role = str(user.role).upper()
    if role not in {"ADMIN", "CONTROL_OFFICER", "MANAGEMENT"} and item.supervisorId != user.user_id:
        raise HTTPException(403, {"code": "EVIDENCE_FORBIDDEN", "message": "You are not assigned to this evidence item"})


def _steps_for_task(state, task_id: str) -> list[WorkStep]:
    """Work steps for a task, from the Postgres-backed state.work_steps
    (flat dict keyed by stepId), ordered for display."""
    return sorted(
        (s for s in state.work_steps.values() if s.taskId == task_id),
        key=lambda s: s.stepIndex,
    )


# -----------------------------------------------------------------------------
# DTOs
# -----------------------------------------------------------------------------
class CreateEvidenceRequest(AuthDTO):
    evidence_id: str
    task_id: str
    step_id: str
    kind: EvidenceKind
    capture_time_utc: str
    start_latitude: float
    start_longitude: float
    gps_accuracy_meters: float
    exception_reason: str | None = None
    idempotency_key: str | None = None


class InitiateUploadRequest(AuthDTO):
    storage_kind: Literal["ORIGINAL", "PROOF"] = "ORIGINAL"
    total_bytes: int = Field(gt=0)
    content_type: str = "image/jpeg"
    part_size_bytes: int = Field(default=8388608, gt=0)


class PartUploadPresignResponse(AuthDTO):
    part_number: int
    upload_url: str
    expires_in_seconds: int = 3600


class UploadPartItem(AuthDTO):
    part_number: int = Field(gt=0)
    etag: str


class CompleteUploadRequest(AuthDTO):
    session_id: str
    storage_kind: Literal["ORIGINAL", "PROOF"]
    parts: list[UploadPartItem] = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    size_bytes: int = Field(gt=0)


class FinalizeEvidenceRequest(AuthDTO):
    location_samples: list[GeoSample] = Field(default_factory=list)
    device_info: dict[str, Any] = Field(default_factory=dict)


class ReviewEvidenceRequest(AuthDTO):
    decision: Literal["ACCEPT", "REJECT"]
    review_notes: str = Field(min_length=1)


# -----------------------------------------------------------------------------
# 1. Authentication Endpoints
# -----------------------------------------------------------------------------
@router.post("/api/v1/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    """Authenticate supervisor with employee ID and password."""
    user = None
    for u in evidence_state.users.values():
        if u.get("employeeId") == req.employee_id:
            user = u
            break

    if not user or not verify_password(user["passwordHash"], req.password):
        raise HTTPException(
            status_code=401,
            detail={"code": "INVALID_CREDENTIALS", "message": "Invalid employee ID or password"},
        )

    if not user.get("active", True):
        raise HTTPException(
            status_code=403,
            detail={"code": "ACCOUNT_DISABLED", "message": "Account has been disabled by an administrator"},
        )

    access_token = create_access_token(user["userId"], user["role"], user["employeeId"], department=user.get("department"))
    raw_refresh, token_hash, expires_at = create_refresh_token()

    evidence_state.refresh_tokens[token_hash] = {
        "userId": user["userId"],
        "expiresAt": expires_at,
        "revoked": False,
    }

    return TokenResponse(
        accessToken=access_token,
        refreshToken=raw_refresh,
        userId=user["userId"],
        role=user["role"],
        employeeId=user["employeeId"],
        name=user["name"],
    )


@router.post("/api/v1/auth/refresh", response_model=TokenResponse)
def refresh_token_endpoint(req: RefreshRequest):
    """Rotate 30-day refresh token and issue new 15-minute access JWT."""
    token_hash = hash_token(req.refresh_token)
    stored = evidence_state.refresh_tokens.get(token_hash)
    if not stored or stored.get("revoked") or stored["expiresAt"] < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=401,
            detail={"code": "REFRESH_TOKEN_INVALID", "message": "Refresh token expired or invalid"},
        )

    # Invalidate old refresh token (token rotation)
    stored["revoked"] = True

    user = evidence_state.users.get(stored["userId"])
    if not user or not user.get("active", True):
        raise HTTPException(status_code=403, detail={"code": "USER_INACTIVE", "message": "User inactive"})

    access_token = create_access_token(user["userId"], user["role"], user["employeeId"], department=user.get("department"))
    raw_new_refresh, new_token_hash, expires_at = create_refresh_token()
    evidence_state.refresh_tokens[new_token_hash] = {
        "userId": user["userId"],
        "expiresAt": expires_at,
        "revoked": False,
    }

    return TokenResponse(
        accessToken=access_token,
        refreshToken=raw_new_refresh,
        userId=user["userId"],
        role=user["role"],
        employeeId=user["employeeId"],
        name=user["name"],
    )


@router.post("/api/v1/auth/logout")
def logout(req: RefreshRequest, current_user: UserAccount = Depends(get_current_user)):
    """Revoke refresh token."""
    token_hash = hash_token(req.refresh_token)
    if token_hash in evidence_state.refresh_tokens:
        evidence_state.refresh_tokens[token_hash]["revoked"] = True
    return {"status": "logged_out"}


@router.get("/api/v1/me")
def get_me(current_user: UserAccount = Depends(get_current_user)):
    """Return currently authenticated user profile and assigned sections."""
    user = evidence_state.users.get(current_user.user_id, {})
    assigned = evidence_state.assignments.get(current_user.user_id, [])
    return {
        "userId": current_user.user_id,
        "employeeId": current_user.employee_id,
        "name": user.get("name", current_user.name),
        "role": current_user.role,
        "email": user.get("email"),
        "department": user.get("department"),
        "assignedSections": assigned,
        "active": user.get("active", True),
    }


# -----------------------------------------------------------------------------
# 2. Supervisor Admin Endpoints
# -----------------------------------------------------------------------------
@router.post("/api/v1/admin/supervisors")
def create_supervisor(
    req: CreateSupervisorRequest, _: UserAccount = Depends(require_role("ADMIN"))
):
    """Admin creates a new supervisor employee account."""
    for u in evidence_state.users.values():
        if u.get("employeeId") == req.employee_id:
            raise HTTPException(400, {"code": "DUPLICATE_EMPLOYEE_ID", "message": "Employee ID exists"})

    user_id = f"sup-{uuid.uuid4().hex[:8]}"
    pwd_hash = hash_password(req.password)
    evidence_state.users[user_id] = {
        "userId": user_id,
        "employeeId": req.employee_id,
        "name": req.name,
        "role": req.role.value,
        "department": req.department,
        "passwordHash": pwd_hash,
        "email": req.email,
        "phone": req.phone,
        "active": True,
        "createdAt": datetime.now(timezone.utc).isoformat(),
    }
    evidence_state.assignments[user_id] = list(req.assigned_section_codes)
    return {"userId": user_id, "employeeId": req.employee_id, "name": req.name}


@router.put("/api/v1/admin/supervisors/{supervisor_id}/areas")
def update_supervisor_areas(
    supervisor_id: str,
    req: UpdateSupervisorAreasRequest,
    _: UserAccount = Depends(require_role("ADMIN")),
):
    """Admin updates assigned sections for a supervisor."""
    if supervisor_id not in evidence_state.users:
        raise HTTPException(404, {"code": "USER_NOT_FOUND", "message": "Supervisor not found"})
    evidence_state.assignments[supervisor_id] = list(req.section_codes)
    return {"supervisorId": supervisor_id, "assignedSections": req.section_codes}


@router.get("/api/v1/admin/supervisors")
def list_supervisors(_: UserAccount = Depends(require_role("ADMIN", "CONTROL_OFFICER"))):
    """List all supervisors and their assigned sections."""
    items = []
    for uid, u in evidence_state.users.items():
        if u.get("role") in {"SUPERVISOR", "FIELD_SUPERVISOR"}:
            items.append({
                "userId": uid,
                "department": u.get("department"),
                "employeeId": u.get("employeeId"),
                "name": u.get("name"),
                "email": u.get("email"),
                "active": u.get("active", True),
                "assignedSections": evidence_state.assignments.get(uid, []),
                "createdAt": u.get("createdAt"),
            })
    return {"items": items, "count": len(items)}


# -----------------------------------------------------------------------------
# 3. Work Assignments and Emergency Reporting
# -----------------------------------------------------------------------------
@router.get("/api/v1/work/assignments/mine")
def get_my_assignments(
    latitude: float | None = Query(None),
    longitude: float | None = Query(None),
    current_user: UserAccount = Depends(get_current_user),
):
    """Get assigned tasks and macro steps for the authenticated supervisor,
    scoped to their own department (ENGG/SNT/TRD) — an SSE/P-Way supervisor
    sees track work, not signal or traction tasks, matching how field staff
    are actually organised by department, not just by section."""
    from .main import state

    assigned_sections = set(evidence_state.assignments.get(current_user.user_id, []))
    user_department = evidence_state.users.get(current_user.user_id, {}).get("department")
    tasks = []

    for t in state.tasks.values():
        task_data = t.model_dump(by_alias=True, mode="json")
        if user_department and task_data.get("department") != user_department:
            continue
        task_id = task_data.get("taskId")
        steps = _steps_for_task(state, task_id)

        # Default fallback steps if none explicitly assigned
        if not steps:
            steps = [
                WorkStep(
                    stepId=f"stp-{task_id}-1",
                    taskId=task_id,
                    stepIndex=1,
                    title="Live Pre-Execution Safety & Site Photo",
                    requiresPhoto=True,
                    targetLatitude=28.6139,
                    targetLongitude=77.2090,
                    targetRadiusMeters=100.0,
                ),
                WorkStep(
                    stepId=f"stp-{task_id}-2",
                    taskId=task_id,
                    stepIndex=2,
                    title="Final Completion & Line Clearance Video (<=90s)",
                    requiresPhoto=False,
                    requiresVideo=True,
                    targetLatitude=28.6139,
                    targetLongitude=77.2090,
                    targetRadiusMeters=100.0,
                ),
            ]
            with state.transaction():
                for step in steps:
                    state.work_steps[step.stepId] = step

        task_data["steps"] = [s.model_dump(by_alias=True, mode="json") for s in steps]
        task_data["executionStatus"] = "IN_PROGRESS" if any(s.status != WorkExecutionStatus.READY for s in steps) else "READY"
        tasks.append(task_data)

    return {
        "supervisorId": current_user.user_id,
        "assignedSections": list(assigned_sections),
        "tasks": tasks,
        "count": len(tasks),
        "asOfUtc": datetime.now(timezone.utc).isoformat(),
    }


@router.post("/api/v1/emergency-reports")
def submit_emergency_report(
    report: EmergencyReport, current_user: UserAccount = Depends(get_current_user)
):
    """Supervisor registers unexpected field damage or safety hazard."""
    from .main import state

    report.supervisorId = current_user.user_id
    report.reportedAtUtc = datetime.now(timezone.utc).isoformat()
    evidence_state.emergency_reports[report.reportId] = report

    state.emit(
        "EMERGENCY_REPORT_CREATED",
        report.reportId,
        report.model_dump(by_alias=True, mode="json"),
        actor=current_user.user_id,
        reason=f"Field supervisor hazard report: {report.hazardType}",
    )
    return {"status": "reported", "reportId": report.reportId}


# -----------------------------------------------------------------------------
# 4. Evidence Upload and Verification Pipeline
# -----------------------------------------------------------------------------
@router.post("/api/v1/evidence")
def create_evidence_item(
    req: CreateEvidenceRequest, current_user: UserAccount = Depends(get_current_user)
):
    """Register intent to capture evidence, binding client UUIDv7 to step and account."""
    from .main import state

    idempotency_key = f"{current_user.user_id}:evidence:{req.idempotency_key}" if req.idempotency_key else None
    if idempotency_key and idempotency_key in evidence_state.idempotency:
        return evidence_state.idempotency[idempotency_key]
    if req.evidence_id in state.evidence_items:
        raise HTTPException(409, {"code": "EVIDENCE_ALREADY_EXISTS", "message": "Evidence ID already exists"})
    step = state.work_steps.get(req.step_id)
    if step is None or step.taskId != req.task_id:
        raise HTTPException(422, {"code": "STEP_NOT_ASSIGNED", "message": "Evidence step is not assigned to the selected task", "details": {"field": "stepId"}})
    # Legacy/demo repositories may retain a task step after the task catalogue
    # has been regenerated. The step binding remains the authoritative check.
    required_kind = EvidenceKind.PHOTO if step.requiresPhoto else EvidenceKind.VIDEO if step.requiresVideo else None
    if required_kind and req.kind != required_kind:
        raise HTTPException(422, {"code": "EVIDENCE_KIND_MISMATCH", "message": f"This step requires {required_kind.value} evidence", "details": {"field": "kind"}})

    item = EvidenceItem(
        evidenceId=req.evidence_id,
        taskId=req.task_id,
        stepId=req.step_id,
        supervisorId=current_user.user_id,
        kind=req.kind,
        status=EvidenceStatus.UPLOAD_PENDING,
        captureTimeUtc=req.capture_time_utc,
        startLatitude=req.start_latitude,
        startLongitude=req.start_longitude,
        gpsAccuracyMeters=req.gps_accuracy_meters,
        geoVerdict=GeoVerdict.WITHIN_RADIUS,
        exceptionReason=req.exception_reason,
        createdTimeUtc=datetime.now(timezone.utc).isoformat(),
        updatedTimeUtc=datetime.now(timezone.utc).isoformat(),
    )
    with state.transaction():
        state.evidence_items[item.evidenceId] = item

    res = item.model_dump(by_alias=True, mode="json")
    if idempotency_key:
        evidence_state.idempotency[idempotency_key] = res
    return res


@router.post("/api/v1/evidence/{evidence_id}/uploads/initiate")
def initiate_upload(
    evidence_id: str,
    req: InitiateUploadRequest,
    current_user: UserAccount = Depends(get_current_user),
):
    """Initiate resilient multipart upload session for original or proof media."""
    from .main import state

    item = state.evidence_items.get(evidence_id)
    if not item:
        raise HTTPException(404, {"code": "EVIDENCE_NOT_FOUND", "message": "Evidence record not found"})
    _authorize_evidence(item, current_user)

    storage_key = f"evidence/{item.taskId}/{item.stepId}/{evidence_id}/{req.storage_kind.lower()}"
    upload_id = object_store.initiate_multipart_upload(storage_key, req.content_type)
    session_id = f"sess-{uuid.uuid4().hex[:12]}"

    total_parts = max(1, (req.total_bytes + req.part_size_bytes - 1) // req.part_size_bytes)
    session_data = {
        "sessionId": session_id,
        "evidenceId": evidence_id,
        "storageKind": req.storage_kind,
        "storageKey": storage_key,
        "uploadId": upload_id,
        "partSizeBytes": req.part_size_bytes,
        "totalParts": total_parts,
        "totalBytes": req.total_bytes,
        "status": "OPEN",
    }
    with state.transaction():
        state.upload_sessions[session_id] = session_data

    return {
        "sessionId": session_id,
        "evidenceId": evidence_id,
        "storageKey": storage_key,
        "uploadId": upload_id,
        "totalParts": total_parts,
        "partSizeBytes": req.part_size_bytes,
    }


@router.post("/api/v1/evidence/{evidence_id}/uploads/parts/{part_number}/presign")
def presign_part_upload(
    evidence_id: str,
    part_number: int,
    session_id: str = Query(..., alias="sessionId"),
    current_user: UserAccount = Depends(get_current_user),
):
    """Generate short-lived presigned URL for direct part upload."""
    from .main import state

    session = state.upload_sessions.get(session_id)
    if not session or session["evidenceId"] != evidence_id:
        raise HTTPException(404, {"code": "SESSION_NOT_FOUND", "message": "Upload session not found"})

    url = object_store.generate_presigned_upload_part_url(
        session["storageKey"], session["uploadId"], part_number
    )
    return PartUploadPresignResponse(
        partNumber=part_number, uploadUrl=url, expiresInSeconds=3600
    )


@router.post("/api/v1/evidence/{evidence_id}/uploads/complete")
def complete_upload(
    evidence_id: str,
    req: CompleteUploadRequest,
    current_user: UserAccount = Depends(get_current_user),
):
    """Complete multipart upload session and store file metadata."""
    from .main import state

    session = state.upload_sessions.get(req.session_id)
    if not session or session["evidenceId"] != evidence_id:
        raise HTTPException(404, {"code": "SESSION_NOT_FOUND", "message": "Upload session not found"})
    if session["storageKind"] != req.storage_kind:
        raise HTTPException(409, {"code": "STORAGE_KIND_MISMATCH", "message": "Upload completion does not match the initiated storage kind"})
    expected_parts = set(range(1, session["totalParts"] + 1))
    supplied_parts = {part.part_number for part in req.parts}
    if supplied_parts != expected_parts:
        raise HTTPException(422, {"code": "UPLOAD_PARTS_INCOMPLETE", "message": "Every initiated upload part must be supplied exactly once", "details": {"expected": sorted(expected_parts), "received": sorted(supplied_parts)}})
    item = state.evidence_items.get(evidence_id)
    if not item:
        raise HTTPException(404, {"code": "EVIDENCE_NOT_FOUND", "message": "Evidence record not found"})
    _authorize_evidence(item, current_user)

    parts_payload = [{"PartNumber": p.part_number, "ETag": p.etag} for p in req.parts]
    object_store.complete_multipart_upload(session["storageKey"], session["uploadId"], parts_payload)
    try:
        stored_bytes = object_store.get_object_bytes(session["storageKey"])
        actual_sha256 = compute_sha256_bytes(stored_bytes)
        if len(stored_bytes) != req.size_bytes or actual_sha256.lower() != req.sha256.lower():
            object_store.delete_object(session["storageKey"])
            raise HTTPException(422, {"code": "UPLOAD_INTEGRITY_MISMATCH", "message": "Uploaded bytes do not match the declared size or SHA-256"})
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(502, {"code": "UPLOAD_NOT_READABLE", "message": "Completed media could not be verified"}) from exc

    with state.transaction():
        session["status"] = "COMPLETED"

        item = state.evidence_items[evidence_id]
        if req.storage_kind == "ORIGINAL":
            item.originalStorageKey = session["storageKey"]
            item.originalSha256 = req.sha256
            item.originalSizeBytes = req.size_bytes
        else:
            item.proofStorageKey = session["storageKey"]
            item.proofSha256 = req.sha256
            item.proofSizeBytes = req.size_bytes

        item.status = EvidenceStatus.UPLOADING
    return {"status": "completed", "storageKey": session["storageKey"]}


@router.post("/api/v1/evidence/{evidence_id}/uploads/abort")
def abort_upload(
    evidence_id: str,
    session_id: str = Query(..., alias="sessionId"),
    current_user: UserAccount = Depends(get_current_user),
):
    """Abort multipart upload session."""
    from .main import state

    with state.transaction():
        session = state.upload_sessions.pop(session_id, None)
        if session and session["evidenceId"] != evidence_id:
            raise HTTPException(404, {"code": "SESSION_NOT_FOUND", "message": "Upload session not found"})
    if session:
        object_store.abort_multipart_upload(session["storageKey"], session["uploadId"])
    return {"status": "aborted"}


@router.post("/api/v1/evidence/{evidence_id}:finalize", status_code=202)
def finalize_evidence(
    evidence_id: str,
    req: FinalizeEvidenceRequest,
    current_user: UserAccount = Depends(get_current_user),
):
    """Finalize evidence submission, enqueue/run durable verification, and sign manifest."""
    from .main import state

    item = state.evidence_items.get(evidence_id)
    if not item:
        raise HTTPException(404, {"code": "EVIDENCE_NOT_FOUND", "message": "Evidence record not found"})
    _authorize_evidence(item, current_user)

    # Find step target
    target_lat = 28.6139
    target_lon = 77.2090
    target_radius = 100.0
    section_code = "SEC_KRJ_SMQ"

    steps = _steps_for_task(state, item.taskId)
    target_step = next((s for s in steps if s.stepId == item.stepId), None)
    if target_step:
        target_lat = target_step.targetLatitude
        target_lon = target_step.targetLongitude
        target_radius = target_step.targetRadiusMeters

    verified_item, signed_manifest = verification_service.verify_evidence(
        item=item,
        target_lat=target_lat,
        target_lon=target_lon,
        target_radius_m=target_radius,
        section_code=section_code,
        location_samples=req.location_samples,
        device_info=req.device_info,
    )

    with state.transaction():
        state.evidence_items[evidence_id] = verified_item

        # Update step status if verified
        if target_step:
            if verified_item.status == EvidenceStatus.VERIFIED:
                target_step.status = WorkExecutionStatus.COMPLETED
                target_step.evidenceId = evidence_id
                state.emit(
                    "TASK_STEP_COMPLETED",
                    target_step.stepId,
                    target_step.model_dump(by_alias=True, mode="json"),
                    actor=current_user.user_id,
                )
            elif verified_item.status == EvidenceStatus.FLAGGED_REVIEW:
                target_step.status = WorkExecutionStatus.COMPLETED_PENDING_EVIDENCE
                target_step.evidenceId = evidence_id
                state.emit(
                    "EVIDENCE_FLAGGED",
                    evidence_id,
                    verified_item.model_dump(by_alias=True, mode="json"),
                    actor=current_user.user_id,
                    reason=verified_item.reviewNotes or "Geospatial or media integrity discrepancy",
                )

    return verified_item.model_dump(by_alias=True, mode="json")


@router.get("/api/v1/evidence/preview-media")
def preview_media(key: str = Query(...)):
    """Serve local object bytes before the dynamic evidence-detail route."""
    if isinstance(object_store, MemoryObjectStore):
        try:
            return Response(content=object_store.get_object_bytes(key),
                            media_type=object_store.get_object_metadata(key).get("content_type", "image/jpeg"))
        except KeyError:
            raise HTTPException(404, {"code": "MEDIA_NOT_FOUND", "message": "Media not found"})
    raise HTTPException(400, {"code": "NOT_SUPPORTED", "message": "Use presigned S3 URLs in production"})


@router.get("/api/v1/evidence/{evidence_id}")
def get_evidence_details(
    evidence_id: str, current_user: UserAccount = Depends(get_current_user)
):
    """Retrieve evidence details with signed media preview URLs and signature status."""
    from .main import state

    item = state.evidence_items.get(evidence_id)
    if not item:
        raise HTTPException(404, {"code": "EVIDENCE_NOT_FOUND", "message": "Evidence record not found"})
    _authorize_evidence(item, current_user)

    data = item.model_dump(by_alias=True, mode="json")
    if item.originalStorageKey:
        data["originalDownloadUrl"] = object_store.generate_presigned_download_url(item.originalStorageKey)
    if item.proofStorageKey:
        data["proofDownloadUrl"] = object_store.generate_presigned_download_url(item.proofStorageKey)

    return data


@router.get("/api/v1/evidence")
def list_evidence(
    status: str | None = None,
    task_id: str | None = None,
    current_user: UserAccount = Depends(get_current_user),
):
    """List evidence items with optional filters."""
    from .main import state

    results = []
    for item in state.evidence_items.values():
        if str(current_user.role).upper() not in {"ADMIN", "CONTROL_OFFICER", "MANAGEMENT"} and item.supervisorId != current_user.user_id:
            continue
        if status and item.status.value != status:
            continue
        if task_id and item.taskId != task_id:
            continue
        row = item.model_dump(by_alias=True, mode="json")
        if item.proofStorageKey:
            row["proofDownloadUrl"] = object_store.generate_presigned_download_url(item.proofStorageKey)
        results.append(row)

    return {"items": results, "count": len(results)}


@router.post("/api/v1/evidence/{evidence_id}:review")
def review_flagged_evidence(
    evidence_id: str,
    req: ReviewEvidenceRequest,
    current_user: UserAccount = Depends(require_role("ADMIN", "CONTROL_OFFICER")),
):
    """Control Officer reviews flagged evidence: ACCEPT_EXCEPTION or REJECT."""
    from .main import state

    item = state.evidence_items.get(evidence_id)
    if not item:
        raise HTTPException(404, {"code": "EVIDENCE_NOT_FOUND", "message": "Evidence not found"})
    _authorize_evidence(item, current_user)

    now_iso = datetime.now(timezone.utc).isoformat()

    with state.transaction():
        if req.decision == "ACCEPT":
            item.status = EvidenceStatus.ACCEPTED_EXCEPTION
        else:
            item.status = EvidenceStatus.REJECTED

        item.reviewerId = current_user.user_id
        item.reviewNotes = req.review_notes
        item.reviewedAt = now_iso
        item.updatedTimeUtc = now_iso

        # Update associated task step
        step = state.work_steps.get(item.stepId)
        if step:
            if item.status == EvidenceStatus.ACCEPTED_EXCEPTION:
                step.status = WorkExecutionStatus.COMPLETED
            else:
                step.status = WorkExecutionStatus.READY  # Retake required

        state.emit(
            "EVIDENCE_REVIEWED",
            evidence_id,
            item.model_dump(by_alias=True, mode="json"),
            actor=current_user.user_id,
            reason=f"Control officer decision: {req.decision}. Notes: {req.review_notes}",
        )

    return item.model_dump(by_alias=True, mode="json")


class DemoEvidenceUploadRequest(AuthDTO):
    task_id: str = "ENG-1001"
    step_id: str | None = None
    kind: EvidenceKind = EvidenceKind.PHOTO
    scenario: Literal["COMPLIANT", "FLAGGED_GPS", "FLAGGED_ACCURACY"] = "COMPLIANT"
    exception_reason: str | None = None
    media_base64: str | None = None


@router.post("/api/v1/evidence/demo-upload")
def demo_upload_evidence(
    req: DemoEvidenceUploadRequest,
    current_user: UserAccount = Depends(get_current_user),
):
    """Simulate a complete field capture, multipart upload, and verification cycle.

    Enables instant field upload demonstration from the web control center or CLI.
    """
    from .main import state
    from .demo_seed import SAMPLE_JPEG_TRACK, SAMPLE_MP4_WALKTHROUGH

    task = state.tasks.get(req.task_id)
    if not task:
        raise HTTPException(404, {"code": "TASK_NOT_FOUND", "message": f"Task {req.task_id} not found"})

    steps = _steps_for_task(state, req.task_id)
    target_step = next((s for s in steps if s.stepId == req.step_id), None) if req.step_id else (steps[0] if steps else None)

    if not target_step:
        target_step = WorkStep(
            stepId=f"stp-{req.task_id}-demo",
            taskId=req.task_id,
            stepIndex=1,
            title="Live Field Execution & Clearance Proof",
            description="Geotagged photographic verification of task completion.",
            requiresPhoto=req.kind == EvidenceKind.PHOTO,
            requiresVideo=req.kind == EvidenceKind.VIDEO,
            targetLatitude=28.6140,
            targetLongitude=77.5030,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.READY,
        )
        with state.transaction():
            state.work_steps[target_step.stepId] = target_step

    target_lat = target_step.targetLatitude
    target_lon = target_step.targetLongitude
    target_radius = target_step.targetRadiusMeters

    scenario_upper = req.scenario.upper()
    if scenario_upper == "FLAGGED_GPS":
        # ~147m distance: outside 100m radius
        start_lat = target_lat + 0.0011
        start_lon = target_lon + 0.0009
        gps_accuracy = 12.0
        reason = req.exception_reason or "Track obstruction or terrain prevented closer standoff; photo captured from authorized access path."
    elif scenario_upper == "FLAGGED_ACCURACY":
        start_lat = target_lat + 0.00003
        start_lon = target_lon + 0.00003
        gps_accuracy = 65.0  # > 50m limit
        reason = req.exception_reason or "Dense tree canopy degraded GPS satellite geometry (accuracy 65m > 50m threshold)."
    else:  # COMPLIANT
        start_lat = target_lat + 0.00004
        start_lon = target_lon + 0.00004
        gps_accuracy = 6.0
        reason = req.exception_reason

    # Resolve media bytes
    if req.media_base64 is not None:
        try:
            media_bytes = base64.b64decode(req.media_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(400, {"code": "INVALID_IMAGE_DATA", "message": "Failed to decode base64 media payload"}) from exc
    elif req.kind == EvidenceKind.VIDEO:
        media_bytes = SAMPLE_MP4_WALKTHROUGH
    else:
        media_bytes = SAMPLE_JPEG_TRACK

    valid_media = (media_bytes.startswith(b"\xff\xd8\xff") if req.kind == EvidenceKind.PHOTO
                   else b"ftyp" in media_bytes[:32])
    if not valid_media:
        raise HTTPException(422, {"code": "INVALID_MEDIA_FORMAT", "message": "Choose a JPEG photo or MP4 video matching the evidence kind"})

    content_type = "video/mp4" if req.kind == EvidenceKind.VIDEO else "image/jpeg"
    sha256_hash = compute_sha256_bytes(media_bytes)
    evidence_id = f"018e{uuid.uuid4().hex[:4]}-{uuid.uuid4().hex[:4]}-7000-8000-{uuid.uuid4().hex[:12]}"
    storage_key = f"evidence/{req.task_id}/{target_step.stepId}/{evidence_id}/proof"

    # Store media in object store
    try:
        object_store.put_object_bytes(storage_key, media_bytes, content_type)
    except Exception as exc:
        raise HTTPException(500, {"code": "STORAGE_ERROR", "message": f"Failed to store media: {exc}"}) from exc

    now_iso = datetime.now(timezone.utc).isoformat()
    raw_item = EvidenceItem(
        evidenceId=evidence_id,
        taskId=req.task_id,
        stepId=target_step.stepId,
        supervisorId=current_user.user_id,
        kind=req.kind,
        status=EvidenceStatus.UPLOADING,
        originalStorageKey=storage_key,
        proofStorageKey=storage_key,
        originalSha256=sha256_hash,
        proofSha256=sha256_hash,
        originalSizeBytes=len(media_bytes),
        proofSizeBytes=len(media_bytes),
        captureTimeUtc=now_iso,
        startLatitude=start_lat,
        startLongitude=start_lon,
        gpsAccuracyMeters=gps_accuracy,
        geoVerdict=GeoVerdict.WITHIN_RADIUS,
        exceptionReason=reason,
        createdTimeUtc=now_iso,
        updatedTimeUtc=now_iso,
    )

    # Run verification pipeline
    verified_item, _ = verification_service.verify_evidence(
        item=raw_item,
        target_lat=target_lat,
        target_lon=target_lon,
        target_radius_m=target_radius,
        section_code=task.sectionId or "SEC_GZB_DER",
    )

    with state.transaction():
        state.evidence_items[evidence_id] = verified_item
        if verified_item.status == EvidenceStatus.VERIFIED:
            target_step.status = WorkExecutionStatus.COMPLETED
            target_step.evidenceId = evidence_id
            state.emit(
                "TASK_STEP_COMPLETED",
                target_step.stepId,
                target_step.model_dump(by_alias=True, mode="json"),
                actor=current_user.user_id,
            )
        elif verified_item.status == EvidenceStatus.FLAGGED_REVIEW:
            target_step.status = WorkExecutionStatus.COMPLETED_PENDING_EVIDENCE
            target_step.evidenceId = evidence_id
            state.emit(
                "EVIDENCE_FLAGGED",
                evidence_id,
                verified_item.model_dump(by_alias=True, mode="json"),
                actor=current_user.user_id,
                reason=verified_item.reviewNotes or "Geospatial discrepancy detected",
            )

    res = verified_item.model_dump(by_alias=True, mode="json")
    res["proofDownloadUrl"] = object_store.generate_presigned_download_url(storage_key)
    return {"evidence": res, "manifest": verified_item.canonicalManifest.model_dump(by_alias=True, mode="json")}

