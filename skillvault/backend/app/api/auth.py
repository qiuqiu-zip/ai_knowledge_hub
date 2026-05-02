from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, get_current_user, get_password_hash, verify_password
from app.db import models
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _to_user_read(user: models.User) -> UserRead:
    return UserRead(
        id=user.id,
        username=user.username,
        is_admin=user.is_admin,
        is_active=user.is_active,
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == payload.username.strip()).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_access_token(subject=user.username, is_admin=user.is_admin)
    return LoginResponse(access_token=token, user=_to_user_read(user))


@router.get("/me", response_model=UserRead)
def me(current_user: models.User = Depends(get_current_user)):
    return _to_user_read(current_user)


def init_admin_user(db: Session) -> None:
    existing = db.query(models.User).count()
    if existing > 0:
        return
    admin_username = (settings.admin_username or "").strip()
    admin_password = settings.admin_password or ""
    if not admin_username or not admin_password:
        return
    user = models.User(
        username=admin_username,
        password_hash=get_password_hash(admin_password),
        is_active=True,
        is_admin=True,
    )
    db.add(user)
    db.commit()
