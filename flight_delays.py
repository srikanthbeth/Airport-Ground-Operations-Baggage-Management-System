from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import (
    UserRole,
    FlightDelayReason,
    FlightDelayStatus,
)
from core.permissions import require_roles
from db.session import get_db
from models.user import User
from schemas.flight_delay import (
    FlightDelayCreate,
    FlightDelayAssignment,
    FlightDelayReview,
    FlightDelayResolve,
    FlightDelayResponse,
    FlightDelayListResponse,
)
from services.flight_delay_service import FlightDelayService


router = APIRouter(
    prefix="/api/v1/flight-delays",
    tags=["Flight Delay Management"],
)


REPORTING_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
    UserRole.GROUND_STAFF_SUPERVISOR,
    UserRole.BAGGAGE_HANDLING_STAFF,
    UserRole.CHECK_IN_AGENT,
    UserRole.GATE_AGENT,
    UserRole.MAINTENANCE_STAFF,
)

MANAGEMENT_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
)


@router.post(
    "/",
    response_model=FlightDelayResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_flight_delay(
    payload: FlightDelayCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTING_ROLES)),
):
    return FlightDelayService.create(db, payload, current_user)


@router.get(
    "/",
    response_model=FlightDelayListResponse,
)
def list_flight_delays(
    flight_id: UUID | None = None,
    delay_status: FlightDelayStatus | None = Query(default=None),
    reason: FlightDelayReason | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTING_ROLES)),
):
    return FlightDelayService.list(
        db=db,
        flight_id=flight_id,
        status_filter=delay_status,
        reason=reason,
        page=page,
        size=size,
    )


@router.get(
    "/{delay_id}",
    response_model=FlightDelayResponse,
)
def get_flight_delay(
    delay_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*REPORTING_ROLES)),
):
    return FlightDelayService.get(db, delay_id)


@router.patch(
    "/{delay_id}/assign",
    response_model=FlightDelayResponse,
)
def assign_flight_delay(
    delay_id: UUID,
    payload: FlightDelayAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return FlightDelayService.assign(
        db,
        delay_id,
        payload.assigned_to_id,
    )


@router.patch(
    "/{delay_id}/review",
    response_model=FlightDelayResponse,
)
def review_flight_delay(
    delay_id: UUID,
    payload: FlightDelayReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return FlightDelayService.review(db, delay_id, payload)


@router.patch(
    "/{delay_id}/resolve",
    response_model=FlightDelayResponse,
)
def resolve_flight_delay(
    delay_id: UUID,
    payload: FlightDelayResolve,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return FlightDelayService.resolve(
        db,
        delay_id,
        payload.resolution_notes,
    )


@router.delete(
    "/{delay_id}",
    status_code=status.HTTP_200_OK,
)
def delete_flight_delay(
    delay_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.AIRPORT_OPERATIONS_MANAGER,
        )
    ),
):
    return FlightDelayService.delete(db, delay_id)