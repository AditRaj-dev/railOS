"""Integration tests for RailOS Field Evidence API, Auth, Multipart Uploads, and Verification."""

import pytest
from fastapi.testclient import TestClient
from railos_api import main as railos_main
from railos_api.evidence_routes import object_store
from railos_api.main import app
from railos_api.storage import MemoryObjectStore
from railos_model import (
    EvidenceKind, EvidenceStatus, GeoVerdict, ManifestSigner, WorkStep,
    compute_sha256_bytes,
)

client = TestClient(app)


def given_work_step(step_id: str, task_id: str, *, index: int = 1, video: bool = False) -> WorkStep:
    """Register the work step this evidence is captured against.

    Work steps are no longer seeded at startup, and finalize refuses evidence
    whose step it cannot find — the step is the only record of where the
    capture had to happen.
    """
    step = WorkStep(
        stepId=step_id, taskId=task_id, stepIndex=index,
        title="Site capture", requiresPhoto=not video, requiresVideo=video,
        targetLatitude=28.6139, targetLongitude=77.2090, targetRadiusMeters=100.0,
    )
    railos_main.state.work_steps[step_id] = step
    return step


def test_auth_login_and_token_rotation():
    # 1. Successful login
    login_res = client.post(
        "/api/v1/auth/login",
        json={"employeeId": "EMP901", "password": "Field@123"},
    )
    assert login_res.status_code == 200, login_res.text
    token_data = login_res.json()
    assert "accessToken" in token_data
    assert "refreshToken" in token_data
    assert token_data["role"] == "SUPERVISOR"
    assert token_data["userId"] == "sup-01"

    access_token = token_data["accessToken"]
    refresh_token = token_data["refreshToken"]

    # 2. Access /api/v1/me with Bearer token
    me_res = client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_res.status_code == 200
    assert me_res.json()["employeeId"] == "EMP901"
    assert "SEC_KRJ_SMQ" in me_res.json()["assignedSections"]

    # 3. Rotate refresh token
    refresh_res = client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert refresh_res.status_code == 200
    new_token_data = refresh_res.json()
    assert new_token_data["accessToken"] != access_token
    new_refresh_token = new_token_data["refreshToken"]

    # 4. Old refresh token should be revoked (replay attack prevention)
    stale_res = client.post(
        "/api/v1/auth/refresh",
        json={"refreshToken": refresh_token},
    )
    assert stale_res.status_code == 401


def test_admin_supervisor_management():
    # Login as admin
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"employeeId": "EMP001", "password": "Admin@123"},
    )
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["accessToken"]

    # Create new supervisor
    create_res = client.post(
        "/api/v1/admin/supervisors",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "employeeId": "EMP905",
            "name": "Amit Sharma",
            "password": "Password@123",
            "role": "SUPERVISOR",
            "assignedSectionCodes": ["SEC_ALJN_KRJ"],
            "department": "ENGG",
        },
    )
    assert create_res.status_code == 200
    created_sup_id = create_res.json()["userId"]
    assert create_res.json()["department"] == "ENGG"

    # A supervisor without a department can never file a ticket
    # (_department_scope returns None -> 403), so the account cannot be
    # created in that state in the first place.
    no_department = client.post(
        "/api/v1/admin/supervisors",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "employeeId": "EMP906",
            "name": "No Department",
            "password": "Password@123",
            "role": "SUPERVISOR",
            "assignedSectionCodes": ["SEC_ALJN_KRJ"],
        },
    )
    assert no_department.status_code == 422

    # Update supervisor assigned areas
    update_res = client.put(
        f"/api/v1/admin/supervisors/{created_sup_id}/areas",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"sectionCodes": ["SEC_ALJN_KRJ", "GZB-ALJN"]},
    )
    assert update_res.status_code == 200
    assert update_res.json()["assignedSections"] == ["SEC_ALJN_KRJ", "GZB-ALJN"]

    # List supervisors
    list_res = client.get(
        "/api/v1/admin/supervisors",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert list_res.status_code == 200
    assert any(s["employeeId"] == "EMP905" for s in list_res.json()["items"])


def test_supervisor_assignments_and_emergency_report():
    # Login as supervisor
    sup_login = client.post(
        "/api/v1/auth/login",
        json={"employeeId": "EMP901", "password": "Field@123"},
    )
    token = sup_login.json()["accessToken"]

    # Fetch mine assignments
    work_res = client.get(
        "/api/v1/work/assignments/mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert work_res.status_code == 200
    tasks = work_res.json()["tasks"]
    assert len(tasks) > 0
    first_task = tasks[0]
    # Steps are reported as they exist. The endpoint used to invent two of them
    # per task, at a fixed Delhi coordinate, and persist them as real.
    assert first_task["steps"] == []

    engg_task = next(t for t in tasks if t["department"] == "ENGG")
    given_work_step("stp-assign-1", engg_task["taskId"])
    with_steps = client.get(
        "/api/v1/work/assignments/mine",
        headers={"Authorization": f"Bearer {token}"},
    )
    listed = next(t for t in with_steps.json()["tasks"] if t["taskId"] == engg_task["taskId"])
    assert [s["stepId"] for s in listed["steps"]] == ["stp-assign-1"]

    # Submit emergency report
    emerg_res = client.post(
        "/api/v1/emergency-reports",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "reportId": "EMERG-001",
            "supervisorId": "sup-01",
            "sectionCode": "SEC_KRJ_SMQ",
            "kmPost": "KM 122/4",
            "latitude": 28.6139,
            "longitude": 77.2090,
            "severity": "IMR",
            "hazardType": "FRACTURED_RAIL",
            "description": "Transverse fracture detected in outer rail under load",
        },
    )
    assert emerg_res.status_code == 200
    assert emerg_res.json()["status"] == "reported"


def test_evidence_lifecycle_multipart_and_verification():
    sup_login = client.post(
        "/api/v1/auth/login",
        json={"employeeId": "EMP901", "password": "Field@123"},
    )
    token = sup_login.json()["accessToken"]

    evidence_id = "018e9999-0000-7000-8000-111122223333"
    task_id = "ENG-1001"
    step_id = "stp-101"
    given_work_step(step_id, task_id)

    # 1. Create evidence record
    create_res = client.post(
        "/api/v1/evidence",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "evidenceId": evidence_id,
            "taskId": task_id,
            "stepId": step_id,
            "kind": "PHOTO",
            "captureTimeUtc": "2026-09-08T10:00:00Z",
            "startLatitude": 28.61395,  # ~5m from target 28.6139
            "startLongitude": 77.20902,
            "gpsAccuracyMeters": 8.0,
        },
    )
    assert create_res.status_code == 200
    assert create_res.json()["status"] == "UPLOAD_PENDING"

    # 2. Initiate multipart upload for original JPEG
    dummy_jpeg = b"\xff\xd8\xff\xe0" + (b"EXIF_DATA_CAMERA_ORIGINAL" * 100)
    orig_sha256 = compute_sha256_bytes(dummy_jpeg)

    init_res = client.post(
        f"/api/v1/evidence/{evidence_id}/uploads/initiate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "storageKind": "ORIGINAL",
            "totalBytes": len(dummy_jpeg),
            "contentType": "image/jpeg",
            "partSizeBytes": len(dummy_jpeg),
        },
    )
    assert init_res.status_code == 200
    session_id = init_res.json()["sessionId"]
    upload_id = init_res.json()["uploadId"]

    # 3. Presign part 1
    presign_res = client.post(
        f"/api/v1/evidence/{evidence_id}/uploads/parts/1/presign?sessionId={session_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert presign_res.status_code == 200
    assert "uploadUrl" in presign_res.json()

    # Simulate direct S3/bucket write in memory store
    if isinstance(object_store, MemoryObjectStore):
        etag = object_store.put_multipart_part(upload_id, 1, dummy_jpeg)
    else:
        etag = '"dummy-etag"'

    # 4. Complete multipart upload
    comp_res = client.post(
        f"/api/v1/evidence/{evidence_id}/uploads/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sessionId": session_id,
            "storageKind": "ORIGINAL",
            "parts": [{"partNumber": 1, "etag": etag}],
            "sha256": orig_sha256,
            "sizeBytes": len(dummy_jpeg),
        },
    )
    assert comp_res.status_code == 200

    # 5. Finalize evidence and run verification
    fin_res = client.post(
        f"/api/v1/evidence/{evidence_id}:finalize",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "locationSamples": [
                {
                    "timestampUtc": "2026-09-08T10:00:00Z",
                    "latitude": 28.61395,
                    "longitude": 77.20902,
                    "accuracyMeters": 8.0,
                    "isMocked": False,
                }
            ],
            "deviceInfo": {"model": "Samsung XCover 6 Pro", "os": "Android 14"},
        },
    )
    assert fin_res.status_code == 202
    result = fin_res.json()
    assert result["status"] == "VERIFIED"
    assert result["geoVerdict"] == "WITHIN_RADIUS"
    assert result["ed25519Signature"] is not None
    assert result["canonicalManifest"] is not None

    # Step status should be updated to COMPLETED
    step = railos_main.state.work_steps[step_id]
    assert step.status == "COMPLETED"


def test_flagged_evidence_and_control_officer_review():
    sup_login = client.post(
        "/api/v1/auth/login",
        json={"employeeId": "EMP901", "password": "Field@123"},
    )
    token = sup_login.json()["accessToken"]

    evidence_id = "018e9999-0000-7000-8000-444455556666"
    task_id = "ENG-1001"
    step_id = "stp-102"
    given_work_step(step_id, task_id, index=2)

    # Out of radius capture (> 500m away)
    client.post(
        "/api/v1/evidence",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "evidenceId": evidence_id,
            "taskId": task_id,
            "stepId": step_id,
            "kind": "PHOTO",
            "captureTimeUtc": "2026-09-08T11:00:00Z",
            "startLatitude": 28.6250,  # ~1.2 km away
            "startLongitude": 77.2150,
            "gpsAccuracyMeters": 12.0,
            "exceptionReason": "Track access blocked by siding construction; photographed from safe vantage point",
        },
    )

    dummy_jpeg = b"\xff\xd8\xff\xe0" + (b"EVIDENCE_DATA" * 50)
    init_res = client.post(
        f"/api/v1/evidence/{evidence_id}/uploads/initiate",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "storageKind": "ORIGINAL",
            "totalBytes": len(dummy_jpeg),
            "contentType": "image/jpeg",
        },
    )
    session_id = init_res.json()["sessionId"]
    upload_id = init_res.json()["uploadId"]

    if isinstance(object_store, MemoryObjectStore):
        etag = object_store.put_multipart_part(upload_id, 1, dummy_jpeg)
    else:
        etag = '"etag"'

    client.post(
        f"/api/v1/evidence/{evidence_id}/uploads/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sessionId": session_id,
            "storageKind": "ORIGINAL",
            "parts": [{"partNumber": 1, "etag": etag}],
            "sha256": compute_sha256_bytes(dummy_jpeg),
            "sizeBytes": len(dummy_jpeg),
        },
    )

    fin_res = client.post(
        f"/api/v1/evidence/{evidence_id}:finalize",
        headers={"Authorization": f"Bearer {token}"},
        json={},
    )
    assert fin_res.status_code == 202
    flagged = fin_res.json()
    assert flagged["status"] == "FLAGGED_REVIEW"
    assert flagged["geoVerdict"] == "OUTSIDE_RADIUS"

    # Control Officer reviews and approves the exception
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"employeeId": "EMP001", "password": "Admin@123"},
    )
    admin_token = admin_login.json()["accessToken"]

    review_res = client.post(
        f"/api/v1/evidence/{evidence_id}:review",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "decision": "ACCEPT",
            "reviewNotes": "Reviewed siding obstruction; vantage point deemed acceptable by Control",
        },
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "ACCEPTED_EXCEPTION"
    assert review_res.json()["reviewerId"] == "admin-01"
