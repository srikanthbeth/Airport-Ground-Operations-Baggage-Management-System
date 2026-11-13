
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from core.constants import (
    UserRole,
    AllocationResourceType,
    ResourceAllocationStatus,
)
from core.permissions import require_roles
from db.session import get_db
from schemas.resource_allocation import (
    ResourceAllocationCreate,
    ResourceAllocationUpdate,
    ResourceAllocationResponse,
)
from services.resource_allocation_service import ResourceAllocationService


router = APIRouter(
    prefix="/api/v1/resource-allocations",
    tags=["Scheduled Resource Allocations"],
)

manager_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
    UserRole.GROUND_STAFF_SUPERVISOR,
)


@router.post(
    "",
    response_model=ResourceAllocationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_allocation(
    data: ResourceAllocationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAllocationService.create(db, data, current_user)


@router.get(
    "",
    response_model=list[ResourceAllocationResponse],
)
def list_allocations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    flight_id: UUID | None = None,
    resource_type: AllocationResourceType | None = None,
    allocation_status: ResourceAllocationStatus | None = Query(
        default=None,
        alias="status",
    ),
    starts_from: datetime | None = None,
    starts_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    if starts_from and starts_to and starts_from > starts_to:
        from fastapi import HTTPException
        raise HTTPException(422, "starts_from cannot be later than starts_to")

    return ResourceAllocationService.list(
        db,
        skip,
        limit,
        flight_id,
        resource_type,
        allocation_status,
        starts_from,
        starts_to,
    )


@router.get(
    "/{allocation_id}",
    response_model=ResourceAllocationResponse,
)
def get_allocation(
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAllocationService.get(db, allocation_id)


@router.patch(
    "/{allocation_id}",
    response_model=ResourceAllocationResponse,
)
def update_allocation(
    allocation_id: UUID,
    data: ResourceAllocationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAllocationService.update(db, allocation_id, data)


@router.patch(
    "/{allocation_id}/activate",
    response_model=ResourceAllocationResponse,
)
def activate_allocation(
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAllocationService.activate(db, allocation_id)


@router.patch(
    "/{allocation_id}/complete",
    response_model=ResourceAllocationResponse,
)
def complete_allocation(
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAllocationService.complete(db, allocation_id)


@router.patch(
    "/{allocation_id}/cancel",
    response_model=ResourceAllocationResponse,
)
def cancel_allocation(
    allocation_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(manager_roles),
):
    return ResourceAllocationService.cancel(db, allocation_id)
