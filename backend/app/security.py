import base64
import hashlib
import hmac
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

DEMO_EMAIL = os.getenv("DEMO_ENGINEER_EMAIL", "engineer@tracegaurd.ai").strip().lower()
DEMO_PASSWORD = os.getenv("DEMO_ENGINEER_PASSWORD", "").strip()
_SECRET = os.getenv("TRACEGAURD_SECRET", "").encode()
SESSION_HOURS = int(os.getenv("SESSION_HOURS", "8"))


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 180_000).hex()


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters")
    salt = secrets.token_bytes(16)
    return base64.urlsafe_b64encode(salt).decode() + "." + _hash_password(password, salt)


def verify_password(password: str, encoded: str | None) -> bool:
    try:
        salt_text, expected = encoded.split(".", 1)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        return hmac.compare_digest(_hash_password(password, salt), expected)
    except Exception:
        return False


def ensure_demo_user() -> None:
    if not DEMO_PASSWORD:
        return
    from .database import SessionLocal, UserRecord
    with SessionLocal() as session:
        user = session.get(UserRecord, DEMO_EMAIL)
        if user is None:
            session.add(UserRecord(email=DEMO_EMAIL, role="SOFTWARE_ENGINEER", password_hash=hash_password(DEMO_PASSWORD), is_active=True))
            session.commit()
        elif not user.password_hash:
            user.password_hash = hash_password(DEMO_PASSWORD)
            user.is_active = True
            session.commit()


def verify_credentials(email: str, password: str) -> bool:
    from .database import SessionLocal, UserRecord
    ensure_demo_user()
    with SessionLocal() as session:
        user = session.get(UserRecord, email.strip().lower())
        return bool(user and user.is_active and verify_password(password, user.password_hash))


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


def issue_token(email: str) -> str:
    if not _SECRET:
        raise RuntimeError("TRACEGAURD_SECRET is required")
    payload = f"{email.lower()}|{int(time.time()) + SESSION_HOURS * 3600}|{secrets.token_urlsafe(24)}"
    signature = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{payload}|{signature}".encode()).decode()
    persist_session(email, token)
    return token


def session_is_active(token: str, email: str) -> bool:
    from .database import SessionLocal, SessionRecord
    with SessionLocal() as session:
        record = session.query(SessionRecord).filter(SessionRecord.token_hash == _token_hash(token), SessionRecord.email == email.lower(), SessionRecord.revoked.is_(False)).first()
        if not record:
            return False
        expires = record.expires_at.replace(tzinfo=timezone.utc) if record.expires_at.tzinfo is None else record.expires_at
        return expires > datetime.now(timezone.utc)


def verify_token(token: str) -> str | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        email, expires, nonce, signature = raw.rsplit("|", 3)
        expected = hmac.new(_SECRET, f"{email}|{expires}|{nonce}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires) < int(time.time()):
            return None
        return email if session_is_active(token, email) else None
    except Exception:
        return None


def revoke_session(token: str) -> None:
    from .database import SessionLocal, SessionRecord
    with SessionLocal() as session:
        record = session.query(SessionRecord).filter(SessionRecord.token_hash == _token_hash(token)).first()
        if record:
            record.revoked = True
            session.commit()
