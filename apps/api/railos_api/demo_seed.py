"""Demonstration data seeding for RailOS.

Seeds realistic, deterministic demo data across the three core departments (ENGG, SNT, TRD):
  1. Department Tickets (BlockRequests) linked to canonical maintenance tasks
  2. Macro Work Steps with GPS coordinates on the GZB-ALJN corridor
  3. Geotagged Field Evidence Items (VERIFIED, FLAGGED_REVIEW, ACCEPTED_EXCEPTION)
     with valid JPEG/MP4 media stored in the object store, complete with Ed25519
     cryptographic signatures and permanent watermark manifests.
"""

from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any

# Deterministic ISO timestamp for seeded records so state.reset() produces identical bytes across calls
STATIC_DEMO_SEED_TIME = "2026-03-01T06:00:00+00:00"

from railos_model import (
    BlockRequest,
    BlockRequestStatus,
    BlockType,
    DataProvenance,
    Department,
    EvidenceItem,
    EvidenceKind,
    EvidenceStatus,
    GeoVerdict,
    ManifestSigner,
    TaskType,
    Track,
    WorkExecutionStatus,
    WorkStep,
    compute_sha256_bytes,
)

# -----------------------------------------------------------------------------
# Valid Minimal JPEGs for Proof Derivatives and Media Gallery
# -----------------------------------------------------------------------------
SAMPLE_JPEG_TRACK = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////"
    "////////////////////////////////////////////////////wgALCAAEAAQBAREA"
    "/8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
)

SAMPLE_JPEG_TAMPING = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////"
    "////////////////////////////////////////////////////wgALCAAEAAQBAREA"
    "/8QAFhABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
)

SAMPLE_JPEG_POINT = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////"
    "////////////////////////////////////////////////////wgALCAAEAAQBAREA"
    "/8QAGBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
)

SAMPLE_JPEG_OHE = base64.b64decode(
    "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP//////////////////////////////////"
    "////////////////////////////////////////////////////wgALCAAEAAQBAREA"
    "/8QAGRABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPxA="
)

SAMPLE_MP4_WALKTHROUGH = (
    b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2avc1mp41"
    b"\x00\x00\x00\x08free"
    b"\x00\x00\x00\x40mdat"
    b"RAILOS_DEMO_WALKTHROUGH_VIDEO_SAMPLE_TRACK_CLEARANCE_FOOTAGE_STREAM"
)


def seed_demo_work_steps(repo: Any) -> int:
    """Populate ordered macro work steps for primary demo tasks across all 3 departments."""
    steps = [
        # TSK-0001 (legacy test task)
        WorkStep(
            stepId="stp-101",
            taskId="TSK-0001",
            stepIndex=1,
            title="Pre-work Site Inspection & Ballast Profile",
            description="Photograph the initial ballast shoulder and check fishplate clearances.",
            requiresPhoto=True,
            requiresVideo=False,
            targetLatitude=28.6139,
            targetLongitude=77.2090,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.COMPLETED,
        ),
        WorkStep(
            stepId="stp-102",
            taskId="TSK-0001",
            stepIndex=2,
            title="Tamping Machine Alignment & Depth Verification",
            description="Photograph tamper tines penetrating sleeper crib to prescribed depth.",
            requiresPhoto=True,
            requiresVideo=False,
            targetLatitude=28.6141,
            targetLongitude=77.2093,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.COMPLETED,
        ),
        WorkStep(
            stepId="stp-103",
            taskId="TSK-0001",
            stepIndex=3,
            title="Post-Tamping Final Track Geometry Walkthrough",
            description="Continuous walkthrough video verifying cross-level, alignment, and track clear of equipment.",
            requiresPhoto=False,
            requiresVideo=True,
            targetLatitude=28.6140,
            targetLongitude=77.2091,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.COMPLETED,
        ),
        # ENG-1001 (Ghaziabad-Dadri Plain Track Tamping)
        WorkStep(
            stepId="stp-ENG-1001-1",
            taskId="ENG-1001",
            stepIndex=1,
            title="Pre-Tamping Ballast Shoulder & Crib Inspection",
            description="Photograph sleeper crib packing and track alignment prior to tamper deployment.",
            requiresPhoto=True,
            requiresVideo=False,
            targetLatitude=28.6140,
            targetLongitude=77.5030,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.COMPLETED,
            evidenceId="018e9000-0001-7000-8000-000000000001",
        ),
        WorkStep(
            stepId="stp-ENG-1001-2",
            taskId="ENG-1001",
            stepIndex=2,
            title="CSM Tamper Tines Squeeze Depth Verification",
            description="Verify tines penetrate crib to 15-20mm below sleeper bottom without damaging sleepers.",
            requiresPhoto=True,
            requiresVideo=False,
            targetLatitude=28.6141,
            targetLongitude=77.5032,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.COMPLETED,
            evidenceId="018e9000-0002-7000-8000-000000000002",
        ),
        WorkStep(
            stepId="stp-ENG-1001-3",
            taskId="ENG-1001",
            stepIndex=3,
            title="Post-Tamping Final Track Clearance & Geometry",
            description="Walkthrough video verifying line clearance, gauge, and absence of foreign tools.",
            requiresPhoto=False,
            requiresVideo=True,
            targetLatitude=28.6140,
            targetLongitude=77.5030,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.COMPLETED,
            evidenceId="018e9000-0005-7000-8000-000000000005",
        ),
        # SNT-2002 (Dadri Yard Point Machine Overhaul)
        WorkStep(
            stepId="stp-SNT-2002-1",
            taskId="SNT-2002",
            stepIndex=1,
            title="Point Machine 14A Throw Rod & Lock Bar Clearance",
            description="Photograph switch rail opening and throw rod obstruction tolerance.",
            requiresPhoto=True,
            requiresVideo=False,
            targetLatitude=28.5524,
            targetLongitude=77.5539,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.COMPLETED_PENDING_EVIDENCE,
            evidenceId="018e9000-0003-7000-8000-000000000003",
        ),
        WorkStep(
            stepId="stp-SNT-2002-2",
            taskId="SNT-2002",
            stepIndex=2,
            title="Station Master Correspondence Test & Indication Proof",
            description="Video demonstrating switch normal/reverse correspondence with cabin visual indicator.",
            requiresPhoto=False,
            requiresVideo=True,
            targetLatitude=28.5524,
            targetLongitude=77.5539,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.READY,
        ),
        # TRD-3001 (Ghaziabad-Dadri OHE Inspection)
        WorkStep(
            stepId="stp-TRD-3001-1",
            taskId="TRD-3001",
            stepIndex=1,
            title="OHE Cantilever & Contact Wire Height Check",
            description="Photograph pantograph contact surface and dropper alignment on mast 2040.",
            requiresPhoto=True,
            requiresVideo=False,
            targetLatitude=28.6010,
            targetLongitude=77.5120,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.COMPLETED,
            evidenceId="018e9000-0004-7000-8000-000000000004",
        ),
        WorkStep(
            stepId="stp-TRD-3001-2",
            taskId="TRD-3001",
            stepIndex=2,
            title="Discharge Rod Grounding & Safe Re-energisation",
            description="Verify earthing discharge rods are correctly clamped before PTW handback.",
            requiresPhoto=True,
            requiresVideo=False,
            targetLatitude=28.6010,
            targetLongitude=77.5120,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.READY,
        ),
        # ENG-1004 (Khurja Turnout 102B Renewal)
        WorkStep(
            stepId="stp-ENG-1004-1",
            taskId="ENG-1004",
            stepIndex=1,
            title="Frog Nose & Check Rail Clearance Verification",
            description="Measure flangeway clearance and check ultrasonic flaw marks on crossing nose.",
            requiresPhoto=True,
            requiresVideo=False,
            targetLatitude=28.2562,
            targetLongitude=77.8541,
            targetRadiusMeters=100.0,
            status=WorkExecutionStatus.READY,
        ),
    ]

    for step in steps:
        repo.work_steps[step.stepId] = step
    return len(steps)


def seed_demo_tickets(repo: Any) -> int:
    """Populate realistic department planning tickets linked to canonical maintenance tasks."""
    now_iso = STATIC_DEMO_SEED_TIME
    provenance = DataProvenance(
        synthetic=True,
        label="Synthetic Hackathon Simulation",
        source="RailOS guided ticket intake",
        sourceType="synthetic",
        isOperationallyAuthoritative=False,
        generatedAt=now_iso,
    )

    tickets = [
        BlockRequest(
            requestId="REQ-ENGG-001",
            department=Department.ENGG,
            corridorId="GZB-ALJN",
            sectionId="SEC_GZB_DER",
            assetId="TRACK_SEC_GZB_DER_UP",
            track=Track.UP,
            kmStart=8.2,
            kmEnd=12.4,
            taskType=TaskType.TAMPING,
            severity=6,
            criticality=9,
            dueMinute=2880,
            estimatedDuration=180,
            requestedStart=120,
            requestedEnd=360,
            blockRequired=True,
            blockType=BlockType.TRAFFIC,
            status=BlockRequestStatus.REQUESTED,
            linkedTaskId="ENG-1001",
            requestedBy="rajesh.kumar",
            requestedByRole="ENGINEERING",
            createdAtUtc=now_iso,
            updatedAtUtc=now_iso,
            reason="Cyclic plain track tamping between Ghaziabad and Dadri; TRC track quality index alert.",
            provenance=provenance,
        ),
        BlockRequest(
            requestId="REQ-SNT-001",
            department=Department.SNT,
            corridorId="GZB-ALJN",
            sectionId="SEC_DER_KRJ",
            assetId="POINT_14A_DER",
            track=Track.DOWN,
            kmStart=24.3,
            kmEnd=24.4,
            taskType=TaskType.POINT_MACHINE_MAINT,
            severity=7,
            criticality=9,
            dueMinute=2880,
            estimatedDuration=90,
            requestedStart=180,
            requestedEnd=300,
            blockRequired=True,
            blockType=BlockType.TRAFFIC,
            status=BlockRequestStatus.REQUESTED,
            linkedTaskId="SNT-2002",
            requestedBy="meena.iyer",
            requestedByRole="SIGNAL_TELECOM",
            createdAtUtc=now_iso,
            updatedAtUtc=now_iso,
            reason="Quarterly overhaul and correspondence testing of Point Machine 14A at Dadri yard.",
            provenance=provenance,
        ),
        BlockRequest(
            requestId="REQ-TRD-001",
            department=Department.TRD,
            corridorId="GZB-ALJN",
            sectionId="SEC_GZB_DER",
            assetId="OHE_ELEM_2040_DER",
            track=Track.UP,
            kmStart=8.0,
            kmEnd=13.0,
            taskType=TaskType.OHE_INSPECTION,
            severity=4,
            criticality=7,
            dueMinute=2880,
            estimatedDuration=120,
            requestedStart=60,
            requestedEnd=240,
            blockRequired=True,
            blockType=BlockType.TRAFFIC,
            status=BlockRequestStatus.REQUESTED,
            linkedTaskId="TRD-3001",
            requestedBy="arjun.nair",
            requestedByRole="TRACTION",
            createdAtUtc=now_iso,
            updatedAtUtc=now_iso,
            reason="Routine Tower Wagon visual inspection and dropper wire tension verification.",
            provenance=provenance,
        ),
        BlockRequest(
            requestId="REQ-ENGG-002",
            department=Department.ENGG,
            corridorId="GZB-ALJN",
            sectionId="SEC_KRJ_SMQ",
            assetId="POINT_102B_KRJ",
            track=Track.UP,
            kmStart=52.1,
            kmEnd=52.4,
            taskType=TaskType.TURNOUT_RENEWAL,
            severity=9,
            criticality=10,
            dueMinute=2880,
            estimatedDuration=210,
            requestedStart=240,
            requestedEnd=480,
            blockRequired=True,
            blockType=BlockType.TRAFFIC,
            status=BlockRequestStatus.REQUESTED,
            linkedTaskId="ENG-1004",
            requestedBy="rajesh.kumar",
            requestedByRole="ENGINEERING",
            createdAtUtc=now_iso,
            updatedAtUtc=now_iso,
            reason="Critical high-speed turnout replacement at Khurja Junction; frog nose ultrasonic flaw indication.",
            provenance=provenance,
        ),
        BlockRequest(
            requestId="REQ-SNT-002",
            department=Department.SNT,
            corridorId="GZB-ALJN",
            sectionId="SEC_GZB_DER",
            assetId="TRACK_SEC_GZB_DER_UP",
            track=Track.UP,
            kmStart=9.0,
            kmEnd=11.8,
            taskType=TaskType.TRACK_CIRCUIT_BOND,
            severity=4,
            criticality=7,
            dueMinute=2880,
            estimatedDuration=60,
            requestedStart=120,
            requestedEnd=240,
            blockRequired=True,
            blockType=BlockType.TRAFFIC,
            status=BlockRequestStatus.REQUESTED,
            linkedTaskId="SNT-2001",
            requestedBy="meena.iyer",
            requestedByRole="SIGNAL_TELECOM",
            createdAtUtc=now_iso,
            updatedAtUtc=now_iso,
            reason="Bond replacement and impedance bond continuity verification under co-ordinated block.",
            provenance=provenance,
        ),
        BlockRequest(
            requestId="REQ-TRD-002",
            department=Department.TRD,
            corridorId="GZB-ALJN",
            sectionId="SEC_DER_KRJ",
            assetId="OHE_ELEM_2041_KRJ",
            track=Track.DOWN,
            kmStart=31.2,
            kmEnd=32.0,
            taskType=TaskType.CATENARY_REPLACEMENT,
            severity=8,
            criticality=9,
            dueMinute=4320,
            estimatedDuration=180,
            requestedStart=300,
            requestedEnd=540,
            blockRequired=True,
            blockType=BlockType.TRAFFIC,
            status=BlockRequestStatus.REQUESTED,
            linkedTaskId="TRD-3002",
            requestedBy="arjun.nair",
            requestedByRole="TRACTION",
            createdAtUtc=now_iso,
            updatedAtUtc=now_iso,
            reason="Catenary splice renewal and contact wire tensioning following hot-spot thermo-vision alert.",
            provenance=provenance,
        ),
    ]

    for req in tickets:
        repo.block_requests[req.requestId] = req

    return len(tickets)


def seed_demo_evidence(repo: Any, object_store: Any, verification_service: Any) -> int:
    """Populate authentic verified and flagged evidence items with object store media."""
    now_iso = STATIC_DEMO_SEED_TIME

    items_config = [
        {
            "id": "018e9000-0001-7000-8000-000000000001",
            "task_id": "ENG-1001",
            "step_id": "stp-ENG-1001-1",
            "supervisor_id": "sup-01",
            "kind": EvidenceKind.PHOTO,
            "status": EvidenceStatus.VERIFIED,
            "lat": 28.61404,
            "lon": 77.50304,
            "target_lat": 28.6140,
            "target_lon": 77.5030,
            "accuracy": 6.0,
            "geo_verdict": GeoVerdict.WITHIN_RADIUS,
            "media_bytes": SAMPLE_JPEG_TRACK,
            "content_type": "image/jpeg",
            "review_notes": "Automatically verified by server verification engine",
            "exception_reason": None,
            "reviewer_id": None,
        },
        {
            "id": "018e9000-0002-7000-8000-000000000002",
            "task_id": "ENG-1001",
            "step_id": "stp-ENG-1001-2",
            "supervisor_id": "sup-01",
            "kind": EvidenceKind.PHOTO,
            "status": EvidenceStatus.VERIFIED,
            "lat": 28.61413,
            "lon": 77.50323,
            "target_lat": 28.6141,
            "target_lon": 77.5032,
            "accuracy": 5.0,
            "geo_verdict": GeoVerdict.WITHIN_RADIUS,
            "media_bytes": SAMPLE_JPEG_TAMPING,
            "content_type": "image/jpeg",
            "review_notes": "Automatically verified by server verification engine",
            "exception_reason": None,
            "reviewer_id": None,
        },
        # FLAGGED_REVIEW: Perfect for demonstrating the Control Officer review & decision modal!
        {
            "id": "018e9000-0003-7000-8000-000000000003",
            "task_id": "SNT-2002",
            "step_id": "stp-SNT-2002-1",
            "supervisor_id": "sup-02",
            "kind": EvidenceKind.PHOTO,
            "status": EvidenceStatus.FLAGGED_REVIEW,
            "lat": 28.5537,
            "lon": 77.5542,
            "target_lat": 28.5524,
            "target_lon": 77.5539,
            "accuracy": 12.0,
            "geo_verdict": GeoVerdict.OUTSIDE_RADIUS,
            "media_bytes": SAMPLE_JPEG_POINT,
            "content_type": "image/jpeg",
            "review_notes": "Distance 147.2m exceeded authoritative radius 100.0m",
            "exception_reason": (
                "Point machine switch assembly obscured by track relay cabin construction fence; "
                "photo taken from authorized adjacent access path."
            ),
            "reviewer_id": None,
        },
        # ACCEPTED_EXCEPTION: Already reviewed by Chief Controller with operational justification
        {
            "id": "018e9000-0004-7000-8000-000000000004",
            "task_id": "TRD-3001",
            "step_id": "stp-TRD-3001-1",
            "supervisor_id": "sup-03",
            "kind": EvidenceKind.PHOTO,
            "status": EvidenceStatus.ACCEPTED_EXCEPTION,
            "lat": 28.6022,
            "lon": 77.5131,
            "target_lat": 28.6010,
            "target_lon": 77.5120,
            "accuracy": 9.0,
            "geo_verdict": GeoVerdict.OUTSIDE_RADIUS,
            "media_bytes": SAMPLE_JPEG_OHE,
            "content_type": "image/jpeg",
            "review_notes": "Accepted by Chief Controller: 25kV OHE feeder gantry electrical safety standoff distance rule enforced.",
            "exception_reason": "High-voltage gantry safety corridor prohibited closer tripod setup.",
            "reviewer_id": "admin-01",
            "reviewed_at": now_iso,
        },
        # VERIFIED VIDEO: Walkthrough proof
        {
            "id": "018e9000-0005-7000-8000-000000000005",
            "task_id": "ENG-1001",
            "step_id": "stp-ENG-1001-3",
            "supervisor_id": "sup-01",
            "kind": EvidenceKind.VIDEO,
            "status": EvidenceStatus.VERIFIED,
            "lat": 28.61402,
            "lon": 77.50302,
            "target_lat": 28.6140,
            "target_lon": 77.5030,
            "accuracy": 7.0,
            "geo_verdict": GeoVerdict.WITHIN_RADIUS,
            "media_bytes": SAMPLE_MP4_WALKTHROUGH,
            "content_type": "video/mp4",
            "review_notes": "Automatically verified by server verification engine",
            "exception_reason": None,
            "reviewer_id": None,
        },
    ]

    for cfg in items_config:
        media_bytes = cfg["media_bytes"]
        sha256_hash = compute_sha256_bytes(media_bytes)
        storage_key = f"evidence/{cfg['task_id']}/{cfg['step_id']}/{cfg['id']}/proof"

        # Put media bytes in object store so preview-media works
        if object_store is not None:
            try:
                object_store.put_object_bytes(storage_key, media_bytes, cfg["content_type"])
            except Exception:
                pass

        item = EvidenceItem(
            evidenceId=cfg["id"],
            taskId=cfg["task_id"],
            stepId=cfg["step_id"],
            supervisorId=cfg["supervisor_id"],
            kind=cfg["kind"],
            status=cfg["status"],
            originalStorageKey=storage_key,
            proofStorageKey=storage_key,
            originalSha256=sha256_hash,
            proofSha256=sha256_hash,
            originalSizeBytes=len(media_bytes),
            proofSizeBytes=len(media_bytes),
            captureTimeUtc=now_iso,
            startLatitude=cfg["lat"],
            startLongitude=cfg["lon"],
            gpsAccuracyMeters=cfg["accuracy"],
            geoVerdict=cfg["geo_verdict"],
            exceptionReason=cfg["exception_reason"],
            reviewerId=cfg.get("reviewer_id"),
            reviewNotes=cfg.get("review_notes"),
            reviewedAt=cfg.get("reviewed_at"),
            createdTimeUtc=now_iso,
            updatedTimeUtc=now_iso,
        )

        # Run verification or sign manifest
        if verification_service:
            try:
                verified_item, _ = verification_service.verify_evidence(
                    item=item,
                    target_lat=cfg["target_lat"],
                    target_lon=cfg["target_lon"],
                    target_radius_m=100.0,
                    section_code="SEC_GZB_DER",
                    signed_at_utc=STATIC_DEMO_SEED_TIME,
                )
                if cfg["status"] == EvidenceStatus.ACCEPTED_EXCEPTION:
                    verified_item.status = EvidenceStatus.ACCEPTED_EXCEPTION
                    verified_item.reviewerId = cfg.get("reviewer_id")
                    verified_item.reviewNotes = cfg.get("review_notes")
                    verified_item.reviewedAt = cfg.get("reviewed_at")
                repo.evidence_items[item.evidenceId] = verified_item
                continue
            except Exception:
                pass

        repo.evidence_items[item.evidenceId] = item

    return len(items_config)


def seed_all_demo_data(repo: Any, object_store: Any = None, verification_service: Any = None) -> dict[str, int]:
    """Execute complete seed across work steps, tickets, and evidence."""
    steps_count = seed_demo_work_steps(repo)
    tickets_count = seed_demo_tickets(repo)
    evidence_count = 0
    if object_store and verification_service:
        evidence_count = seed_demo_evidence(repo, object_store, verification_service)

    return {
        "workSteps": steps_count,
        "tickets": tickets_count,
        "evidence": evidence_count,
    }
