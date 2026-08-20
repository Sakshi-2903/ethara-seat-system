"""
Authentication for the Ethara Seat Allocation System.

Simple JWT-based login with three roles:
  - admin / hr : full read-write access (create/update employees, allocate/release seats)
  - employee   : read-only access (search, dashboard, AI assistant, own record)

Demo credentials are created by seed.py:
  admin / admin123
  hr / hr123
  employee / employee123
"""
import os
import datetime
from typing import Optional
import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app import models

# In production, set JWT_SECRET_KEY as a real environment variable/secret.
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-secret-change-me-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 8

bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user: models.User) -> str:
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "employee_id": user.employee_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")


class CurrentUser:
    def __init__(self, user_id: int, username: str, role: str, employee_id: Optional[int]):
        self.id = user_id
        self.username = username
        self.role = role
        self.employee_id = employee_id


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please log in.",
        )
    payload = decode_token(credentials.credentials)
    return CurrentUser(
        user_id=int(payload["sub"]),
        username=payload["username"],
        role=payload["role"],
        employee_id=payload.get("employee_id"),
    )


def require_write_access(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    """Only admin/hr can create, update, allocate, or release."""
    if current_user.role not in ("admin", "hr"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin or HR accounts can perform this action.",
        )
    return current_user


def require_admin(current_user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required.")
    return current_user


def assert_self_or_privileged(current_user: CurrentUser, target_employee_id: Optional[int]) -> None:
    """
    Allows admin/hr to act on any employee_id. Allows an 'employee' role account to act
    only on its own linked employee_id (self-service seat booking/release). Anything else
    is rejected with a 403.
    """
    if current_user.role in ("admin", "hr"):
        return
    if current_user.role == "employee":
        if current_user.employee_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account isn't linked to an employee record, so it can't book a seat.",
            )
        if target_employee_id != current_user.employee_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only book or release a seat for themselves.",
            )
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted.")
