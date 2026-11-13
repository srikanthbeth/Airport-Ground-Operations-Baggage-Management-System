from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import UserRole
from core.permissions import require_roles
from db.session import get_db
from schemas.gate import GateCreate, GateResponse, GateUpdate
from services.gate_service import GateService


router = APIRouter(
    prefix="/api/v1/gates",
    tags=["Gate Management"],
)

manager_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
)


@router.post("/", response_model=GateResponse, status_code=status.HTTP_201_CREATED)
def create_gate(
    data: GateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return GateService.create(db, data)


@router.get("/", response_model=list[GateResponse])
def list_gates(
    terminal_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return GateService.list(db, terminal_id, skip, limit)


@router.get("/{gate_id}", response_model=GateResponse)
def get_gate(
    gate_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return GateService.get(db, gate_id)


@router.patch("/{gate_id}", response_model=GateResponse)
def update_gate(
    gate_id: UUID,
    data: GateUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return GateService.update(db, gate_id, data)