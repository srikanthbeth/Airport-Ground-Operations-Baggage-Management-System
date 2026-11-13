
from sqlalchemy import select

from db.session import SessionLocal
from models.user import User
from core.config import settings
from core.constants import UserRole
from core.security import hash_password


def create_admin():

    db = SessionLocal()

    try:
        email = settings.BOOTSTRAP_ADMIN_EMAIL.lower().strip()

        existing = db.scalar(
            select(User).where(User.email == email)
        )

        if existing:
            print("Super Admin already exists")
            return

        admin = User(
            full_name="Airport Super Administrator",
            email=email,
            hashed_password=hash_password(
                settings.BOOTSTRAP_ADMIN_PASSWORD
            ),
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True
        )

        db.add(admin)
        db.commit()

        print("Super Admin created successfully")

    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
