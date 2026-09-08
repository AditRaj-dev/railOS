"""Canonical evidence manifest serialization, SHA-256 hashing, and Ed25519 signing."""

from __future__ import annotations

import base64
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from .models import EvidenceManifestV1


def canonical_json_bytes(data: Any) -> bytes:
    """Serialize data to deterministic, canonical UTF-8 JSON bytes."""
    return json.dumps(
        data,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def compute_sha256_bytes(data: bytes) -> str:
    """Compute lowercase hex SHA-256 digest of bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_sha256_stream(stream) -> str:
    """Compute lowercase hex SHA-256 digest of a readable byte stream."""
    hasher = hashlib.sha256()
    while chunk := stream.read(65536):
        hasher.update(chunk)
    return hasher.hexdigest()


class ManifestSigner:
    """Ed25519 signer and verifier for RailOS canonical evidence manifests."""

    def __init__(
        self,
        private_key: ed25519.Ed25519PrivateKey | None = None,
        public_key: ed25519.Ed25519PublicKey | None = None,
    ):
        if private_key is not None:
            self._private_key = private_key
            self._public_key = private_key.public_key()
        elif public_key is not None:
            self._private_key = None
            self._public_key = public_key
        else:
            self._private_key = ed25519.Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()

    @classmethod
    def from_private_bytes(cls, raw_bytes: bytes) -> ManifestSigner:
        """Load from 32-byte raw private key or PKCS8 bytes."""
        if len(raw_bytes) == 32:
            key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
        else:
            key = serialization.load_pem_private_key(raw_bytes, password=None)
        return cls(private_key=key)

    @classmethod
    def from_public_bytes(cls, raw_bytes: bytes) -> ManifestSigner:
        """Load from 32-byte raw public key or SubjectPublicKeyInfo bytes."""
        if len(raw_bytes) == 32:
            key = ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)
        else:
            key = serialization.load_pem_public_key(raw_bytes)
        return cls(public_key=key)

    @property
    def public_bytes(self) -> bytes:
        """Export raw 32-byte public key."""
        return self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )

    @property
    def public_hex(self) -> str:
        return self.public_bytes.hex()

    def canonicalize_for_signing(self, manifest: EvidenceManifestV1 | dict[str, Any]) -> bytes:
        """Prepare canonical payload for signature calculation by stripping signature fields."""
        if isinstance(manifest, EvidenceManifestV1):
            raw = manifest.model_dump(by_alias=True)
        else:
            raw = dict(manifest)

        # Exclude server signature fields from the signed content
        raw.pop("serverSignature", None)
        raw.pop("signedAtUtc", None)

        return canonical_json_bytes(raw)

    def sign_manifest(
        self,
        manifest: EvidenceManifestV1 | dict[str, Any],
        signed_at_utc: datetime | None = None,
    ) -> EvidenceManifestV1:
        """Sign canonical manifest using Ed25519 and return signed EvidenceManifestV1."""
        if self._private_key is None:
            raise ValueError("Cannot sign without private key")

        timestamp = (signed_at_utc or datetime.now(timezone.utc)).isoformat()
        canonical_bytes = self.canonicalize_for_signing(manifest)
        signature = self._private_key.sign(canonical_bytes)
        signature_b64 = base64.b64encode(signature).decode("ascii")

        if isinstance(manifest, EvidenceManifestV1):
            data = manifest.model_dump(by_alias=True)
        else:
            data = dict(manifest)

        data["signedAtUtc"] = timestamp
        data["serverSignature"] = signature_b64

        return EvidenceManifestV1.model_validate(data)

    def verify_manifest(self, manifest: EvidenceManifestV1 | dict[str, Any]) -> bool:
        """Verify the Ed25519 signature of an EvidenceManifestV1."""
        if isinstance(manifest, EvidenceManifestV1):
            data = manifest.model_dump(by_alias=True)
        else:
            data = dict(manifest)

        sig_b64 = data.get("serverSignature")
        if not sig_b64:
            return False

        try:
            signature = base64.b64decode(sig_b64)
            canonical_bytes = self.canonicalize_for_signing(data)
            self._public_key.verify(signature, canonical_bytes)
            return True
        except (InvalidSignature, ValueError):
            return False
