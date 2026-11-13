from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.session import get_db
from routes.auth import get_current_user
from core.permissions import require_roles
from core.constants import UserRole
from core.constants import UserRole, AircraftTurnaroundStatus

from schemas.aircraft_turnaround import (
    AircraftTurnaroundCreate,
    AircraftTurnaroundUpdate,
    AircraftTurnaroundStatusUpdate,
    TurnaroundMilestoneUpdate,
    AircraftTurnaroundResponse,
    AircraftTurnaroundListResponse,
)
from services.aircraft_turnaround_service import (
    create_turnaround,
    get_turnaround,
    list_turnarounds,
    update_turnaround,
    update_turnaround_status,
    record_milestone,
)

router = APIRouter(
    prefix="/api/v1/aircraft-turnarounds",
    tags=["Aircraft Turnarounds"],
)

MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.GROUND_STAFF_SUPERVISOR,
]


@router.post("/", response_model=AircraftTurnaroundResponse, status_code=201)
def create_aircraft_turnaround(
    data: AircraftTurnaroundCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return create_turnaround(db, data.model_dump(), current_user)


@router.get("/", response_model=AircraftTurnaroundListResponse)
def get_aircraft_turnarounds(
    airport_id: str | None = None,
    flight_id: str | None = None,
    status: AircraftTurnaroundStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return list_turnarounds(
        db,
        airport_id=airport_id,
        flight_id=flight_id,
        status=status,
        page=page,
        page_size=page_size,
    )


@router.get("/{turnaround_id}", response_model=AircraftTurnaroundResponse)
def get_aircraft_turnaround(
    turnaround_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_turnaround(db, turnaround_id)


@router.patch("/{turnaround_id}", response_model=AircraftTurnaroundResponse)
def update_aircraft_turnaround(
    turnaround_id: str,
    data: AircraftTurnaroundUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return update_turnaround(
        db,
        turnaround_id,
        data.model_dump(exclude_unset=True),
    )


@router.patch("/{turnaround_id}/status", response_model=AircraftTurnaroundResponse)
def change_aircraft_turnaround_status(
    turnaround_id: str,
    data: AircraftTurnaroundStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return update_turnaround_status(db, turnaround_id, data.status)


@router.post("/{turnaround_id}/milestones", response_model=AircraftTurnaroundResponse)
def add_aircraft_turnaround_milestone(
    turnaround_id: str,
    data: TurnaroundMilestoneUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return record_milestone(
        db,
        turnaround_id,
        data.milestone,
        data.completed_at,
    )