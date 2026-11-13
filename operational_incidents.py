from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from db.session import get_db
from core.permissions import require_roles
from core.constants import UserRole

from schemas.operational_incident import (
    OperationalIncidentCreate,
    OperationalIncidentUpdate,
    OperationalIncidentResponse,
    OperationalIncidentListResponse,
    IncidentAssignment,
    IncidentStatusUpdate,
)

from services.operational_incident_service import (
    OperationalIncidentService,
)


router = APIRouter(
    prefix="/api/v1/operational-incidents",
    tags=["Operational Incident Management"],
)


INCIDENT_STAFF_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
    UserRole.GROUND_STAFF_SUPERVISOR,
    UserRole.BAGGAGE_HANDLING_STAFF,
    UserRole.CHECK_IN_AGENT,
    UserRole.GATE_AGENT,
    UserRole.MAINTENANCE_STAFF,
]


INCIDENT_MANAGEMENT_ROLES = [
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.FLIGHT_OPERATIONS_OFFICER,
    UserRole.GROUND_STAFF_SUPERVISOR,
    UserRole.MAINTENANCE_STAFF,
]


@router.post(
    "/",
    response_model=OperationalIncidentResponse,
    status_code=201,
)
def create_incident(
    data: OperationalIncidentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*INCIDENT_STAFF_ROLES)),
):
    return OperationalIncidentService.create(db, data, current_user)


@router.get(
    "/",
    response_model=OperationalIncidentListResponse,
)
def list_incidents(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    airport_id: UUID | None = None,
    category: str | None = None,
    severity: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*INCIDENT_MANAGEMENT_ROLES)),
):
    items, total = OperationalIncidentService.list(
        db=db,
        skip=skip,
        limit=limit,
        airport_id=airport_id,
        category=category,
        severity=severity,
        status=status,
    )

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get(
    "/{incident_id}",
    response_model=OperationalIncidentResponse,
)
def get_incident(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*INCIDENT_MANAGEMENT_ROLES)),
):
    return OperationalIncidentService.get(db, incident_id)


@router.patch(
    "/{incident_id}",
    response_model=OperationalIncidentResponse,
)
def update_incident(
    incident_id: UUID,
    data: OperationalIncidentUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*INCIDENT_MANAGEMENT_ROLES)),
):
    return OperationalIncidentService.update(db, incident_id, data)


@router.patch(
    "/{incident_id}/assign",
    response_model=OperationalIncidentResponse,
)
def assign_incident(
    incident_id: UUID,
    data: IncidentAssignment,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*INCIDENT_MANAGEMENT_ROLES)),
):
    return OperationalIncidentService.assign(db, incident_id, data)


@router.patch(
    "/{incident_id}/status",
    response_model=OperationalIncidentResponse,
)
def update_incident_status(
    incident_id: UUID,
    data: IncidentStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*INCIDENT_MANAGEMENT_ROLES)),
):
    return OperationalIncidentService.update_status(
        db, incident_id, data
    )


@router.delete(
    "/{incident_id}",
)
def delete_incident(
    incident_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(
        require_roles(
            UserRole.SUPER_ADMIN,
            UserRole.AIRPORT_OPERATIONS_MANAGER,
        )
    ),
):
    return OperationalIncidentService.delete(db, incident_id)