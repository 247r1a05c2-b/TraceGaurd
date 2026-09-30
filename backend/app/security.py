import base64
import hashlib
import hmac
import os
import time

DEMO_EMAIL = os.getenv("DEMO_ENGINEER_EMAIL", "engineer@tracegaurd.ai")
DEMO_PASSWORD = os.getenv("DEMO_ENGINEER_PASSWORD", "TraceGaurd@123")
_SECRET = os.getenv("TRACEGAURD_SECRET", "tracegaurd-demo-secret-change-me").encode()


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 120_000).hex()


def _stored_hash(password: str) -> str:
    salt = hashlib.sha256(b"tracegaurd-demo-salt").digest()[:16]
    return base64.urlsafe_b64encode(salt).decode() + "." + _hash_password(password, salt)


def verify_credentials(email: str, password: str) -> bool:
    return hmac.compare_digest(email.strip().lower(), DEMO_EMAIL.lower()) and hmac.compare_digest(_stored_hash(password), _stored_hash(DEMO_PASSWORD))


def issue_token(email: str) -> str:
    payload = f"{email.lower()}|{int(time.time()) + 8 * 3600}"
    signature = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{payload}|{signature}".encode()).decode()


def verify_token(token: str) -> str | None:
    try:
        raw = base64.urlsafe_b64decode(token.encode()).decode()
        email, expires, signature = raw.rsplit("|", 2)
        expected = hmac.new(_SECRET, f"{email}|{expires}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(expires) < int(time.time()):
            return None
        return email
    except Exception:
        return None
