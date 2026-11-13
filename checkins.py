from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.constants import UserRole
from core.permissions import require_roles
from db.session import get_db
from schemas.checkin import (
    CheckInCancelResponse,
    CheckInCreate,
    CheckInResponse,
)
from services import checkin_service

router = APIRouter(
    prefix="/api/v1/checkins",
    tags=["Check-ins"],
)


CHECKIN_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.CHECK_IN_AGENT,
)


@router.post(
    "/",
    response_model=CheckInResponse,
    status_code=201,
)
def create_checkin(
    data: CheckInCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*CHECKIN_ROLES)),
):
    return checkin_service.create_checkin(db, data)


@router.get("/", response_model=list[CheckInResponse])
def list_checkins(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    flight_id: UUID | None = None,
    passenger_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*CHECKIN_ROLES)),
):
    return checkin_service.get_checkins(
        db,
        skip=skip,
        limit=limit,
        flight_id=flight_id,
        passenger_id=passenger_id,
    )


@router.get("/{checkin_id}", response_model=CheckInResponse)
def get_checkin(
    checkin_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*CHECKIN_ROLES)),
):
    return checkin_service.get_checkin(db, checkin_id)


@router.patch(
    "/{checkin_id}/cancel",
    response_model=CheckInCancelResponse,
)
def cancel_checkin(
    checkin_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*CHECKIN_ROLES)),
):
    checkin = checkin_service.cancel_checkin(db, checkin_id)

    return {
        "message": "Check-in cancelled successfully",
        "checkin_id": checkin.id,
        "status": checkin.status,
    }