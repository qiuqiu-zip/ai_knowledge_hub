from __future__ import annotations

import sys

from app.core.config import settings
from app.core.security import get_password_hash
from app.db import models
from app.db.session import SessionLocal


def main() -> int:
    username = (settings.admin_username or "").strip()
    password = settings.admin_password or ""
    if not username or not password:
        print("ADMIN_USERNAME / ADMIN_PASSWORD is required")
        return 1

    with SessionLocal() as db:
        user = db.query(models.User).filter(models.User.username == username).first()
        if not user:
            user = models.User(username=username, password_hash=get_password_hash(password), is_active=True, is_admin=True)
            db.add(user)
            db.commit()
            print(f"admin created: {username}")
            return 0

        user.password_hash = get_password_hash(password)
        user.is_active = True
        user.is_admin = True
        db.commit()
        print(f"admin updated: {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
