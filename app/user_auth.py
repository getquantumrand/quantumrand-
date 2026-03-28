"""User authentication: signup, login, JWT tokens."""

import bcrypt
import jwt
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request

from app.config import JWT_SECRET
from app.database import create_user, get_user_by_email, get_user_by_id, get_usage_stats, _hash_key


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def signup(email: str, password: str) -> dict:
    """Create user account, return user info + JWT token."""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")

    pw_hash = hash_password(password)
    user = create_user(email, pw_hash)
    token = create_token(user["user_id"], email)
    return {**user, "token": token}


def login(email: str, password: str) -> dict:
    """Authenticate user, return JWT token."""
    user = get_user_by_email(email)
    if not user:
        raise ValueError("Invalid email or password")

    if not verify_password(password, user["password_hash"]):
        raise ValueError("Invalid email or password")

    token = create_token(user["user_id"], user["email"])
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "tier": user.get("tier", "free"),
        "token": token,
    }


def get_current_user(request: Request) -> dict:
    """Extract and validate JWT from cookie or Authorization header."""
    token = request.cookies.get("qr_token")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(token)
    user = get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user
