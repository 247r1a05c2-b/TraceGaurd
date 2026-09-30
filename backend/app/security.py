import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

DEMO_EMAIL = os.getenv("DEMO_ENGINEER_EMAIL", "engineer@tracegaurd.ai").strip().lower()
DEMO_PASSWORD = os.getenv("DEMO_ENGINEER_PASSWORD", "TraceGaurd@123")
_SECRET = os.getenv("TRACEGAURD_SECRET", "tracegaurd-demo-secret-change-me").encode()
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000).hex()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    return base64.urlsafe_b64encode(salt).decode() + "." + _hash_password(password, salt)


def verify_password(password: str, encoded: str | None) -> bool:
    try:
        salt_text, expected = encoded.split(".", 1)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        actual = _hash_password(password, salt)
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def _legacy_stored_hash(password: str) -> str:
    salt = hashlib.sha256(b"tracegaurd-demo-salt").digest()[:16]
    return base64.urlsafe_b64encode(salt).decode() + "." + _hash_password(password, salt)


def verify_credentials(email: str, password: str) -> bool:
    return hmac.compare_digest(email.strip().lower(), DEMO_EMAIL) and hmac.compare_digest(_legacy_stored_hash(password), _legacy_stored_hash(DEMO_PASSWORD))


def issue_token(email: str) -> str:
    payload = f"{email.lower()}|{int(time.time()) + SESSION_HOURS * 3600}|{secrets.token_urlsafe(24)}"
    signature = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{signature}".encode()).decode()


def verify_token(token: str) -> str | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        email, expires, nonce, signature = raw.rsplit("|", 3)
        expected = hmac.new(_SECRET, f"{email}|{expires}|{nonce}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires) < int(time.time()):
            return None
        return email
    except Exception:
        return None


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def persist_session(email: str, token: str) -> str:
    from .database import SessionLocal, SessionRecord
    session_id = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_HOURS)
    with SessionLocal() as session:
        session.add(SessionRecord(id=session_id, email=email.lower(), token_hash=_token_hash(token), expires_at=expires_at.replace(tzinfo=None), revoked=False))
        session.commit()
    return session_id


def session_is_active(token: str, email: str) -> bool:
    from .database import SessionLocal, SessionRecord
    with SessionLocal() as session:
        record = session.query(SessionRecord).filter(SessionRecord.token_hash == _token_hash(token), SessionRecord.email == email.lower(), SessionRecord.revoked.is_(False)).first()
        if not record:
            return False
        expires = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
        return expires > datetime.now(timezone.utc)


def revoke_session(token: str) -> None:
    from .database import SessionLocal, SessionRecord
    with SessionLocal() as session:
        record = session.query(SessionRecord).filter(SessionRecord.token_hash == _token_hash(token)).first()
        if record:
            record.revoked = True
            session.commit()
