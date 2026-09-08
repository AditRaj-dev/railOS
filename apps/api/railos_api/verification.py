"""Durable verification engine for RailOS field evidence.

Performs independent server-side SHA-256 recalculation, media header validation,
authoritative geospatial distance calculations, exception classification, and
Ed25519 canonical manifest signing.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from railos_model import (
    EvidenceItem,
    EvidenceKind,
    EvidenceManifestV1,
    EvidenceStatus,
    EvidenceTargetSnapshot,
    GeoSample,
    GeoVerdict,
    ManifestSigner,
    WorkExecutionStatus,
    compute_sha256_bytes,
)

from .storage import ObjectStore

# Haversine distance in meters
EARTH_RADIUS_METERS = 6371000.0


def calculate_haversine_distance_meters(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """Calculate great-circle distance between two points on WGS84 sphere in meters."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


class EvidenceVerificationService:
    """Core verification service that audits captured evidence and signs manifests."""

    def __init__(self, object_store: ObjectStore, signer: ManifestSigner | None = None):
        self.store = object_store
        self.signer = signer or ManifestSigner()

    def verify_evidence(
        self,
        item: EvidenceItem,
        target_lat: float,
        target_lon: float,
        target_radius_m: float = 100.0,
        section_code: str = "",
        km_post: str = "",
        location_samples: list[GeoSample] | None = None,
        device_info: dict[str, Any] | None = None,
    ) -> tuple[EvidenceItem, EvidenceManifestV1]:
        """Perform authoritative server verification of evidence items."""
        now_utc = datetime.now(timezone.utc).isoformat()
        flag_reasons: list[str] = []

        # 1. Fetch media objects and recalculate hashes
        orig_bytes = b""
        proof_bytes = b""
        computed_orig_sha256 = ""
        computed_proof_sha256 = ""

        if item.originalStorageKey:
            try:
                orig_bytes = self.store.get_object_bytes(item.originalStorageKey)
                computed_orig_sha256 = compute_sha256_bytes(orig_bytes)
                if item.originalSha256 and item.originalSha256.lower() != computed_orig_sha256.lower():
                    flag_reasons.append(
                        f"Original SHA-256 mismatch: client={item.originalSha256} vs server={computed_orig_sha256}"
                    )
            except Exception as e:
                flag_reasons.append(f"Failed to retrieve original media object: {e}")

        if item.proofStorageKey:
            try:
                proof_bytes = self.store.get_object_bytes(item.proofStorageKey)
                computed_proof_sha256 = compute_sha256_bytes(proof_bytes)
                if item.proofSha256 and item.proofSha256.lower() != computed_proof_sha256.lower():
                    flag_reasons.append(
                        f"Proof SHA-256 mismatch: client={item.proofSha256} vs server={computed_proof_sha256}"
                    )
            except Exception as e:
                flag_reasons.append(f"Failed to retrieve proof media object: {e}")

        # 2. Media format integrity checks
        if item.kind == EvidenceKind.PHOTO:
            if orig_bytes and not orig_bytes.startswith(b"\xff\xd8\xff"):
                flag_reasons.append("Original file is not a valid JPEG")
            if proof_bytes and not proof_bytes.startswith(b"\xff\xd8\xff"):
                flag_reasons.append("Proof derivative is not a valid JPEG")
        elif item.kind == EvidenceKind.VIDEO:
            if orig_bytes and b"ftyp" not in orig_bytes[:32]:
                flag_reasons.append("Original video is not a valid MP4/ISO container")

        # 3. Authoritative Geospatial Distance Calculation
        distance_m = calculate_haversine_distance_meters(
            item.startLatitude, item.startLongitude, target_lat, target_lon
        )

        verdict = GeoVerdict.WITHIN_RADIUS
        if item.gpsAccuracyMeters > 50.0:
            verdict = GeoVerdict.LOW_ACCURACY
            flag_reasons.append(f"GPS accuracy {item.gpsAccuracyMeters}m exceeded 50m target")
        elif distance_m > target_radius_m:
            verdict = GeoVerdict.OUTSIDE_RADIUS
            flag_reasons.append(
                f"Distance {distance_m:.1f}m exceeded authoritative radius {target_radius_m:.1f}m"
            )

        # 4. Check location traces for mocked flags
        samples = location_samples or []
        if any(s.isMocked for s in samples):
            verdict = GeoVerdict.MOCKED_LOCATION
            flag_reasons.append("Mocked location provider detected during capture")

        # 5. Determine final verdict & status
        if flag_reasons:
            status = EvidenceStatus.FLAGGED_REVIEW
            review_notes = "; ".join(flag_reasons)
        else:
            status = EvidenceStatus.VERIFIED
            review_notes = "Automatically verified by server verification engine"

        # 6. Build and sign canonical manifest
        target_snapshot = EvidenceTargetSnapshot(
            latitude=target_lat,
            longitude=target_lon,
            radiusMeters=target_radius_m,
            sectionCode=section_code,
            kmPost=km_post,
        )

        unsigned_manifest = EvidenceManifestV1(
            manifestVersion="1.0",
            evidenceId=item.evidenceId,
            taskId=item.taskId,
            stepId=item.stepId,
            supervisorId=item.supervisorId,
            kind=item.kind,
            captureStartTimeUtc=item.captureTimeUtc,
            captureEndTimeUtc=now_utc,
            originalSha256=computed_orig_sha256 or (item.originalSha256 or ""),
            proofSha256=computed_proof_sha256 or (item.proofSha256 or ""),
            originalSizeBytes=len(orig_bytes) if orig_bytes else (item.originalSizeBytes or 0),
            proofSizeBytes=len(proof_bytes) if proof_bytes else (item.proofSizeBytes or 0),
            mediaProperties={
                "originalBytes": len(orig_bytes),
                "proofBytes": len(proof_bytes),
                "kind": item.kind.value,
            },
            targetLocation=target_snapshot,
            locationSamples=samples,
            geoVerdict=verdict,
            distanceToTargetMeters=distance_m,
            exceptionReason=item.exceptionReason,
            deviceInfo=device_info or {},
            clientCreatedTimeUtc=item.captureTimeUtc,
        )

        signed_manifest = self.signer.sign_manifest(unsigned_manifest)

        # 7. Update item properties
        updated_item = item.model_copy(
            update={
                "status": status,
                "originalSha256": signed_manifest.originalSha256,
                "proofSha256": signed_manifest.proofSha256,
                "originalSizeBytes": signed_manifest.originalSizeBytes,
                "proofSizeBytes": signed_manifest.proofSizeBytes,
                "distanceToTargetMeters": distance_m,
                "geoVerdict": verdict,
                "reviewNotes": review_notes,
                "canonicalManifest": signed_manifest,
                "ed25519Signature": signed_manifest.serverSignature,
                "updatedTimeUtc": now_utc,
            }
        )

        return updated_item, signed_manifest
