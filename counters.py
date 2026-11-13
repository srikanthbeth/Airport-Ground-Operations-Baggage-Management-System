from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import UserRole
from core.permissions import require_roles
from db.session import get_db
from schemas.checkin_counter import (
    CounterCreate,
    CounterResponse,
    CounterUpdate,
)
from services.counter_service import CounterService


router = APIRouter(
    prefix="/api/v1/counters",
    tags=["Check-in Counter Management"],
)

manager_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
)


@router.post(
    "/",
    response_model=CounterResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_counter(
    data: CounterCreate,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return CounterService.create(db, data)


@router.get("/", response_model=list[CounterResponse])
def list_counters(
    terminal_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return CounterService.list(db, terminal_id, skip, limit)


@router.get("/{counter_id}", response_model=CounterResponse)
def get_counter(
    counter_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return CounterService.get(db, counter_id)


@router.patch("/{counter_id}", response_model=CounterResponse)
def update_counter(
    counter_id: UUID,
    data: CounterUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return CounterService.update(db, counter_id, data)