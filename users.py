
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.session import get_db
from models.user import User
from core.constants import UserRole
from core.permissions import require_roles
from schemas.user import AdminCreateUser, UserStatusResponse
from schemas.auth import UserResponse
from services import user_service


router = APIRouter(
    prefix="/api/v1/users",
    tags=["User Management"]
)


admin_required = require_roles(UserRole.SUPER_ADMIN)


@router.post(
    "/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED
)
def create_user(
    data: AdminCreateUser,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    try:
        return user_service.create_staff_user(db, data)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )


@router.get(
    "/",
    response_model=list[UserResponse]
)
def list_users(
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    return user_service.get_all_users(db)


@router.patch(
    "/{user_id}/activate",
    response_model=UserStatusResponse
)
def activate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    try:
        return user_service.change_user_status(
            db,
            user_id,
            True
        )

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch(
    "/{user_id}/deactivate",
    response_model=UserStatusResponse
)
def deactivate_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required)
):

    if user_id == admin.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot deactivate your own account"
        )

    try:
        return user_service.change_user_status(
            db,
            user_id,
            False
        )

    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
