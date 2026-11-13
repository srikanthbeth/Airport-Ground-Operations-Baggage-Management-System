from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.constants import IdentificationType, PassengerStatus, UserRole
from core.permissions import require_roles
from db.session import get_db
from schemas.passenger import (
    PassengerCreate,
    PassengerResponse,
    PassengerUpdate,
)
from services.passenger_service import PassengerService


router = APIRouter(
    prefix="/api/v1/passengers",
    tags=["Passenger Management"],
)


MANAGEMENT_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
    UserRole.GROUND_STAFF_SUPERVISOR,
    UserRole.CHECK_IN_AGENT
)

READ_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
    UserRole.GROUND_STAFF_SUPERVISOR,
    UserRole.BAGGAGE_HANDLING_STAFF,
    UserRole.CHECK_IN_AGENT,
    UserRole.GATE_AGENT,
)


@router.post(
    "/",
    response_model=PassengerResponse,
    status_code=201,
)
def create_passenger(
    data: PassengerCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return PassengerService.create(db, data)


@router.get(
    "/",
    response_model=list[PassengerResponse],
)
def list_passengers(
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    flight_id: UUID | None = None,
    status: PassengerStatus | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*READ_ROLES)),
):
    return PassengerService.list(
        db,
        skip,
        limit,
        search,
        flight_id,
        status,
    )


@router.get(
    "/history/{identification_type}/{identification_number}",
    response_model=list[PassengerResponse],
)
def passenger_history(
    identification_type: IdentificationType,
    identification_number: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*READ_ROLES)),
):
    return PassengerService.history(
        db,
        identification_type,
        identification_number,
    )


@router.get(
    "/{passenger_id}",
    response_model=PassengerResponse,
)
def get_passenger(
    passenger_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*READ_ROLES)),
):
    return PassengerService.get(db, passenger_id)


@router.patch(
    "/{passenger_id}",
    response_model=PassengerResponse,
)
def update_passenger(
    passenger_id: UUID,
    data: PassengerUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return PassengerService.update(db, passenger_id, data)


@router.patch(
    "/{passenger_id}/cancel",
    response_model=PassengerResponse,
)
def cancel_passenger(
    passenger_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return PassengerService.cancel(db, passenger_id)