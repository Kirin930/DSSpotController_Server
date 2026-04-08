from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


PBKDF2_ITERATIONS = 390000


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode(f"{raw}{padding}".encode("ascii"))


def hash_secret(secret: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{PBKDF2_ITERATIONS}${_b64encode(salt)}${_b64encode(digest)}"


def verify_secret(secret: str, encoded_hash: str) -> bool:
    try:
        iterations_raw, salt_raw, digest_raw = encoded_hash.split("$", maxsplit=2)
        iterations = int(iterations_raw)
        salt = _b64decode(salt_raw)
        expected = _b64decode(digest_raw)
    except (TypeError, ValueError):
        return False

    actual = hashlib.pbkdf2_hmac(
        "sha256", secret.encode("utf-8"), salt, iterations
    )
    return hmac.compare_digest(actual, expected)


def generate_token(length: int = 32) -> str:
    return secrets.token_urlsafe(length)


def _sign(secret_key: str, value: str) -> str:
    signature = hmac.new(
        secret_key.encode("utf-8"),
        value.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return signature


def _build_signed_payload(secret_key: str, payload: dict[str, Any]) -> str:
    encoded_payload = _b64encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _sign(secret_key, encoded_payload)
    return f"{encoded_payload}.{signature}"


def _parse_signed_payload(secret_key: str, token: str) -> dict[str, Any] | None:
    try:
        encoded_payload, signature = token.split(".", maxsplit=1)
    except ValueError:
        return None

    expected = _sign(secret_key, encoded_payload)
    if not hmac.compare_digest(signature, expected):
        return None

    try:
        payload = json.loads(_b64decode(encoded_payload))
    except (json.JSONDecodeError, ValueError):
        return None
    return payload


def build_session_token(secret_key: str, username: str, ttl_seconds: int) -> str:
    payload = {
        "sub": username,
        "exp": int(time.time()) + ttl_seconds,
        "nonce": secrets.token_hex(8),
        "kind": "session",
    }
    return _build_signed_payload(secret_key, payload)


def parse_session_token(secret_key: str, token: str) -> str | None:
    payload = _parse_signed_payload(secret_key, token)
    if payload is None or payload.get("kind") != "session":
        return None

    if int(payload.get("exp", 0)) < int(time.time()):
        return None
    return str(payload.get("sub")) if payload.get("sub") else None


def build_csrf_token(secret_key: str, username: str, ttl_seconds: int) -> str:
    payload = {
        "sub": username,
        "exp": int(time.time()) + ttl_seconds,
        "nonce": secrets.token_hex(16),
        "kind": "csrf",
    }
    return _build_signed_payload(secret_key, payload)


def verify_csrf_token(secret_key: str, token: str, username: str) -> bool:
    payload = _parse_signed_payload(secret_key, token)
    if payload is None or payload.get("kind") != "csrf":
        return False
    if int(payload.get("exp", 0)) < int(time.time()):
        return False
    return hmac.compare_digest(str(payload.get("sub", "")), username)


def build_download_signature(
    secret_key: str, node_id: str, spot_id: str, expires: int
) -> str:
    return _sign(secret_key, f"{node_id}:{spot_id}:{expires}")


def verify_download_signature(
    secret_key: str, node_id: str, spot_id: str, expires: int, signature: str
) -> bool:
    if expires < int(time.time()):
        return False
    expected = build_download_signature(secret_key, node_id, spot_id, expires)
    return hmac.compare_digest(signature, expected)


def serialize_for_json(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, mode="json")
    return value
