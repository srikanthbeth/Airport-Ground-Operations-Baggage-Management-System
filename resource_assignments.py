from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import UserRole
from core.permissions import require_roles
from db.session import get_db
from schemas.resource_assignment import (
    ResourceAssignmentCreate,
    ResourceAssignmentResponse,
)
from services.resource_assignment_service import ResourceAssignmentService


router = APIRouter(
    prefix="/api/v1/resource-assignments",
    tags=["Gate and Counter Assignments"],
)

manager_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
)


@router.post(
    "/gates/{gate_id}",
    response_model=ResourceAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_gate(
    gate_id: UUID,
    data: ResourceAssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAssignmentService.assign_gate(
        db,
        gate_id,
        data.flight_id,
    )


@router.post(
    "/counters/{counter_id}",
    response_model=ResourceAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def assign_counter(
    counter_id: UUID,
    data: ResourceAssignmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAssignmentService.assign_counter(
        db,
        counter_id,
        data.flight_id,
    )


@router.patch(
    "/{assignment_id}/release",
    response_model=ResourceAssignmentResponse,
)
def release_assignment(
    assignment_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAssignmentService.release(db, assignment_id)


@router.get(
    "/gates/{gate_id}/history",
    response_model=list[ResourceAssignmentResponse],
)
def gate_assignment_history(
    gate_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAssignmentService.gate_history(
        db,
        gate_id,
        skip,
        limit,
    )


@router.get(
    "/counters/{counter_id}/history",
    response_model=list[ResourceAssignmentResponse],
)
def counter_assignment_history(
    counter_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAssignmentService.counter_history(
        db,
        counter_id,
        skip,
        limit,
    )