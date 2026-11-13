from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import FlightStatus, UserRole
from core.permissions import require_roles
from db.session import get_db
from routes.auth import get_current_user
from schemas.flight import (
    FlightCreate,
    FlightResponse,
    FlightStatusUpdate,
    FlightUpdate,
)
from services.flight_service import FlightService


router = APIRouter(
    prefix="/api/v1/flights",
    tags=["Flight Management"],
)

flight_management_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
)


@router.post(
    "/",
    response_model=FlightResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_flight(
    data: FlightCreate,
    db: Session = Depends(get_db),
    current_user=Depends(flight_management_roles),
):
    return FlightService.create_flight(db, data)


@router.get("/", response_model=list[FlightResponse])
def list_flights(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=200),
    flight_status: FlightStatus | None = Query(default=None),
    origin_airport_id: UUID | None = Query(default=None),
    destination_airport_id: UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return FlightService.list_flights(
        db=db,
        skip=skip,
        limit=limit,
        status_filter=flight_status,
        origin_airport_id=origin_airport_id,
        destination_airport_id=destination_airport_id,
    )


@router.get("/{flight_id}", response_model=FlightResponse)
def get_flight(
    flight_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return FlightService.get_flight(db, flight_id)


@router.patch("/{flight_id}", response_model=FlightResponse)
def update_flight(
    flight_id: UUID,
    data: FlightUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(flight_management_roles),
):
    return FlightService.update_flight(db, flight_id, data)


@router.patch(
    "/{flight_id}/status",
    response_model=FlightResponse,
)
def update_flight_status(
    flight_id: UUID,
    data: FlightStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(flight_management_roles),
):
    return FlightService.update_flight_status(
        db,
        flight_id,
        data.status,
    )