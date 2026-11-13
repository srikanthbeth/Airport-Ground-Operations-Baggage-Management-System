from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.constants import UserRole
from core.permissions import require_roles
from db.session import get_db
from schemas.terminal import TerminalCreate, TerminalResponse, TerminalUpdate
from services.terminal_service import (
    create_terminal,
    deactivate_terminal,
    get_terminal,
    list_terminals,
    update_terminal,
)

router = APIRouter(prefix="/api/v1/terminals", tags=["Terminals"])

terminal_managers = [
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
]


@router.post(
    "/", response_model=TerminalResponse, status_code=status.HTTP_201_CREATED
)
def create_terminal_endpoint(
    data: TerminalCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*terminal_managers)),
):
    terminal = create_terminal(db, data)

    if terminal is None:
        raise HTTPException(404, "Airport not found or inactive")
    if terminal is False:
        raise HTTPException(409, "Terminal code already exists in this airport")

    return terminal


@router.get("/", response_model=list[TerminalResponse])
def list_terminals_endpoint(
    airport_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*terminal_managers)),
):
    return list_terminals(db, airport_id, skip, limit)


@router.get("/{terminal_id}", response_model=TerminalResponse)
def get_terminal_endpoint(
    terminal_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*terminal_managers)),
):
    terminal = get_terminal(db, terminal_id)
    if not terminal:
        raise HTTPException(404, "Terminal not found")
    return terminal


@router.patch("/{terminal_id}", response_model=TerminalResponse)
def update_terminal_endpoint(
    terminal_id: UUID,
    data: TerminalUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*terminal_managers)),
):
    terminal = get_terminal(db, terminal_id)
    if not terminal:
        raise HTTPException(404, "Terminal not found")

    return update_terminal(db, terminal, data)


@router.patch("/{terminal_id}/deactivate", response_model=TerminalResponse)
def deactivate_terminal_endpoint(
    terminal_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*terminal_managers)),
):
    terminal = get_terminal(db, terminal_id)
    if not terminal:
        raise HTTPException(404, "Terminal not found")

    return deactivate_terminal(db, terminal)