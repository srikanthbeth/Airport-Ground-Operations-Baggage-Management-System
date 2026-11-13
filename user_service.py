
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.user import User
from core.constants import UserRole
from core.security import hash_password


def create_staff_user(db: Session, data):

    email = str(data.email).strip().lower()

    existing = db.scalar(
        select(User).where(User.email == email)
    )

    if existing:
        raise ValueError("Email already registered")

    user = User(
        full_name=data.full_name.strip(),
        email=email,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_active=True,
        is_verified=False
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_all_users(db: Session):

    return db.scalars(
        select(User).order_by(User.created_at.desc())
    ).all()


def change_user_status(
    db: Session,
    user_id,
    is_active: bool
):

    user = db.get(User, user_id)

    if not user:
        raise ValueError("User not found")

    user.is_active = is_active

    db.commit()
    db.refresh(user)

    return user
