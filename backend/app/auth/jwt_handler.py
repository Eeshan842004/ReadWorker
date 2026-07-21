import datetime

import bcrypt
from jose import JWTError, jwt

from app.config import settings

# bcrypt operates on the first 72 bytes of a password and errors on longer input in 5.x.
BCRYPT_MAX_BYTES = 72

# NOTE: we call bcrypt directly rather than going through passlib. passlib 1.7.4 (last
# released 2020) is incompatible with bcrypt >= 4.1 and raises a spurious
# "password cannot be longer than 72 bytes" on short passwords.


def _to_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_to_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_to_bytes(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": subject,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=settings.JWT_EXPIRY_MINUTES),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
