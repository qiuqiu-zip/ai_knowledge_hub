from fastapi import Depends, Header, HTTPException, status
from app.core.config import settings


def verify_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    if not settings.admin_token:
        return
    if x_admin_token != settings.admin_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")


AdminGuard = Depends(verify_admin_token)
