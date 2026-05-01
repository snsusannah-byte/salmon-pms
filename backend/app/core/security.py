from datetime import datetime, timedelta, timezone
from typing import Optional
import hashlib
import secrets

import jwt

from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（使用 PBKDF2）"""
    try:
        salt, stored_hash = hashed_password.split("$", 1)
        salt_bytes = bytes.fromhex(salt)
        computed = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt_bytes, 100000)
        return secrets.compare_digest(computed.hex(), stored_hash)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """哈希密码（使用 PBKDF2）"""
    salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + "$" + hashed.hex()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # Ensure sub is a string for PyJWT 2.x compatibility
    if "sub" in to_encode and to_encode["sub"] is not None:
        to_encode["sub"] = str(to_encode["sub"])
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except jwt.PyJWTError:
        return None
