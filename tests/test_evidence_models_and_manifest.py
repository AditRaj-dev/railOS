"""Tests for RailOS Field Evidence models, canonical manifest serialization, and Ed25519 signing."""

import pytest
from railos_model import (
    EvidenceKind,
    EvidenceManifestV1,
    EvidenceStatus,
    EvidenceTargetSnapshot,
    GeoSample,
    GeoVerdict,
    ManifestSigner,
    UserRole,
    WorkExecutionStatus,
    WorkStep,
    canonical_json_bytes,
    compute_sha256_bytes,
)


def test_evidence_enums_and_work_steps():
    assert EvidenceKind.PHOTO == "PHOTO"
    assert EvidenceKind.VIDEO == "VIDEO"
    assert WorkExecutionStatus.COMPLETED == "COMPLETED"
    assert EvidenceStatus.FLAGGED_REVIEW == "FLAGGED_REVIEW"
    assert GeoVerdict.WITHIN_RADIUS == "WITHIN_RADIUS"
    assert UserRole.SUPERVISOR == "SUPERVISOR"

    step = WorkStep(
        stepId="step-001",
        taskId="task-101",
        stepIndex=1,
        title="Check fishplate bolt tightness",
        requiresPhoto=True,
        requiresVideo=False,
        targetLatitude=28.6139,
        targetLongitude=77.2090,
        targetRadiusMeters=100.0,
        status=WorkExecutionStatus.READY,
    )
    assert step.stepId == "step-001"
    assert step.status == WorkExecutionStatus.READY


def test_manifest_signer_and_tamper_detection():
    signer = ManifestSigner()
    verifier = ManifestSigner.from_public_bytes(signer.public_bytes)

    manifest_data = EvidenceManifestV1(
        evidenceId="018e1234-5678-7000-8000-123456789abc",
        taskId="task-101",
        stepId="step-001",
        supervisorId="sup-99",
        kind=EvidenceKind.PHOTO,
        captureStartTimeUtc="2026-09-08T10:00:00Z",
        originalSha256="a" * 64,
        proofSha256="b" * 64,
        originalSizeBytes=2_048_000,
        proofSizeBytes=1_850_000,
        mediaProperties={"width": 1920, "height": 1080, "mimeType": "image/jpeg"},
        targetLocation=EvidenceTargetSnapshot(
            latitude=28.6139,
            longitude=77.2090,
            radiusMeters=100.0,
            sectionCode="NDLS-GZB",
            kmPost="KM 14/2",
        ),
        locationSamples=[
            GeoSample(
                timestampUtc="2026-09-08T10:00:00Z",
                latitude=28.61392,
                longitude=77.20905,
                accuracyMeters=8.5,
                isMocked=False,
            )
        ],
        geoVerdict=GeoVerdict.WITHIN_RADIUS,
        distanceToTargetMeters=5.2,
        deviceInfo={"model": "Pixel 7a", "osVersion": "Android 14"},
        clientCreatedTimeUtc="2026-09-08T10:00:01Z",
    )

    signed_manifest = signer.sign_manifest(manifest_data)
    assert signed_manifest.serverSignature is not None
    assert signed_manifest.signedAtUtc is not None

    # Verification should succeed with public key
    assert verifier.verify_manifest(signed_manifest) is True

    # Tamper test 1: Change original SHA-256 by 1 character
    tampered_data = signed_manifest.model_dump()
    tampered_data["originalSha256"] = "c" + ("a" * 63)
    assert verifier.verify_manifest(tampered_data) is False

    # Tamper test 2: Alter captured coordinate
    tampered_coord = signed_manifest.model_dump()
    tampered_coord["locationSamples"][0]["latitude"] = 28.69999
    assert verifier.verify_manifest(tampered_coord) is False

    # Tamper test 3: Alter distance or verdict
    tampered_verdict = signed_manifest.model_dump()
    tampered_verdict["geoVerdict"] = GeoVerdict.OUTSIDE_RADIUS.value
    assert verifier.verify_manifest(tampered_verdict) is False


def test_canonical_json_is_deterministic():
    obj_a = {"z": 1, "a": 2, "m": [3, 2, 1], "sub": {"b": True, "a": False}}
    obj_b = {"a": 2, "sub": {"a": False, "b": True}, "z": 1, "m": [3, 2, 1]}

    assert canonical_json_bytes(obj_a) == canonical_json_bytes(obj_b)
    assert compute_sha256_bytes(canonical_json_bytes(obj_a)) == compute_sha256_bytes(
        canonical_json_bytes(obj_b)
    )
