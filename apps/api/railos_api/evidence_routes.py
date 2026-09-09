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
from .user_store import user_store_factory
from .verification import EvidenceVerificationService

router = APIRouter(tags=["field-evidence"])
object_store = get_object_store()
verification_service = EvidenceVerificationService(object_store)


# -----------------------------------------------------------------------------
# In-Memory State for Auth, Assignments, Evidence, and Work Steps
# -----------------------------------------------------------------------------
class FieldEvidenceState:
    """Auth/assignment state.

    Users, refresh tokens and section assignments come from `user_store`
    (the `users` table under postgres, a dict for tests) - they used to be
    four hardcoded accounts with shipped passwords that reset on restart.
    Evidence items, work steps and upload sessions live in the Postgres-backed
    `state` repository from main.py instead (see COLLECTIONS).

    Emergency reports and idempotency keys stay in-process: both are
    session-scoped and neither is read after a restart.
    """

    def __init__(self):
        store = user_store_factory()
        self.users = store.users
        self.refresh_tokens = store.refresh_tokens
        self.assignments = store.assignments
        self.emergency_reports: dict[str, EmergencyReport] = {}
        self.idempotency: dict[str, Any] = {}


evidence_state = FieldEvidenceState()


def _authorize_evidence(item: EvidenceItem, user: UserAccount) -> None:
    """Keep evidence media and review metadata scoped to its owner or reviewers."""
    role = str(user.role).upper()
    if role not in {"ADMIN", "CONTROL_OFFICER", "MANAGEMENT"} and item.supervisorId != user.user_id:
        raise HTTPException(403, {"code": "EVIDENCE_FORBIDDEN", "message": "You are not assigned to this evidence item"})


def _section_for_task(state, task_id: str) -> str | None:
    """The task's own section. Evidence used to be stamped SEC_KRJ_SMQ."""
    task = state.tasks.get(task_id)
    return getattr(task, "sectionId", None) if task else None


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
        department=user.get("department"),
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
        department=user.get("department"),
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
    return {
        "userId": user_id,
        "employeeId": req.employee_id,
        "name": req.name,
        "department": req.department,
    }


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

        # A task with no work steps has none. Inventing two — with a fixed
        # Delhi coordinate — meant evidence was verified against a location
        # nobody surveyed, and the invented steps were then persisted as real.
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


class WorkStepInput(AuthDTO):
    """One step of a task's work plan, and where its evidence must be captured."""

    step_id: str | None = None
    title: str = Field(min_length=1)
    description: str = ""
    requires_photo: bool = True
    requires_video: bool = False
    target_latitude: float = Field(ge=-90, le=90)
    target_longitude: float = Field(ge=-180, le=180)
    target_radius_meters: float = Field(default=100.0, gt=0)


class DefineWorkStepsRequest(AuthDTO):
    steps: list[WorkStepInput] = Field(min_length=1)


@router.put("/api/v1/tasks/{task_id}/steps")
def define_work_steps(
    task_id: str,
    req: DefineWorkStepsRequest,
    current_user: UserAccount = Depends(require_role("ADMIN", "CONTROL_OFFICER", "PLANNER")),
):
    """Define the work steps for a task.

    Nothing could create these before: the assignments endpoint invented two
    per task at a fixed coordinate and persisted them, so every task appeared
    to have a surveyed capture location it had never been given. Evidence
    verification refuses a step it cannot find, so this is where the location
    an inspector is held to actually comes from.
    """
    from .main import state

    task = state.tasks.get(task_id)
    if task is None:
        raise HTTPException(404, {"code": "TASK_NOT_FOUND", "message": "task does not exist"})

    steps = [
        WorkStep(
            stepId=item.step_id or f"stp-{task_id}-{index}",
            taskId=task_id,
            stepIndex=index,
            title=item.title,
            description=item.description,
            requiresPhoto=item.requires_photo,
            requiresVideo=item.requires_video,
            targetLatitude=item.target_latitude,
            targetLongitude=item.target_longitude,
            targetRadiusMeters=item.target_radius_meters,
        )
        for index, item in enumerate(req.steps, start=1)
    ]
    step_ids = [step.stepId for step in steps]
    if len(set(step_ids)) != len(step_ids):
        raise HTTPException(422, {"code": "DUPLICATE_STEP_ID", "message": "step ids must be unique", "details": {"field": "steps"}})

    with state.transaction():
        for existing in [s for s in state.work_steps.values() if s.taskId == task_id]:
            del state.work_steps[existing.stepId]
        for step in steps:
            state.work_steps[step.stepId] = step
        state.emit(
            "TASK_STEPS_DEFINED", task_id,
            {"taskId": task_id, "stepIds": step_ids},
            actor=current_user.user_id,
        )

    return {"taskId": task_id, "steps": [s.model_dump(by_alias=True, mode="json") for s in steps], "count": len(steps)}


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

    # The work step is the only authority on where this evidence had to be
    # captured. Falling back to a fixed coordinate meant evidence was verified
    # against a point in Delhi and signed as if that had been checked.
    steps = _steps_for_task(state, item.taskId)
    target_step = next((s for s in steps if s.stepId == item.stepId), None)
    if target_step is None:
        raise HTTPException(422, {
            "code": "WORK_STEP_REQUIRED",
            "message": "evidence cannot be verified without the work step that defines its capture location",
            "details": {"field": "stepId", "taskId": item.taskId, "stepId": item.stepId},
        })
    target_lat = target_step.targetLatitude
    target_lon = target_step.targetLongitude
    target_radius = target_step.targetRadiusMeters
    section_code = _section_for_task(state, item.taskId)
    if not section_code:
        raise HTTPException(422, {
            "code": "TASK_SECTION_REQUIRED",
            "message": "evidence cannot be signed without the task's section",
            "details": {"field": "taskId", "taskId": item.taskId},
        })

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
def preview_media(
    key: str = Query(...),
    current_user: UserAccount = Depends(get_current_user),
):
    """Serve local object bytes before the dynamic evidence-detail route.

    Authenticated: this streams field evidence media, and anyone holding a
    storage key could previously download it with no credentials at all.
    """
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
