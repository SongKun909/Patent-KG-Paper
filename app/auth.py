"""JWT authentication utilities."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from jose import jwt

from app.config import settings


def hash_password(password: str) -> str:
    """Hash password using PBKDF2-SHA256 with random salt."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000)
    return f"pbkdf2:sha256:100000${salt}${dk.hex()}"


def verify_password(plain: str, hashed: str) -> bool:
    """Verify password against PBKDF2 hash."""
    try:
        algo, digest, iterations, rest = hashed.split("$", 3)
        salt, stored = rest.split("$")
        dk = hashlib.pbkdf2_hmac(
            digest.replace("pbkdf2:", ""),
            plain.encode(),
            salt.encode(),
            int(iterations),
        )
        return hmac.compare_digest(dk.hex(), stored)
    except (ValueError, AttributeError):
        return False


def create_access_token(user_id: int, username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRE_HOURS)
    payload = {"sub": str(user_id), "username": username, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except Exception:
        return None
