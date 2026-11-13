from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.constants import UserRole
from core.permissions import require_roles
from db.session import get_db
from schemas.airport import AirportCreate, AirportResponse, AirportUpdate
from services.airport_service import (
    create_airport,
    deactivate_airport,
    get_airport,
    list_airports,
    update_airport,
)

router = APIRouter(prefix="/api/v1/airports", tags=["Airports"])

airport_managers = [
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
]


@router.post(
    "/", response_model=AirportResponse, status_code=status.HTTP_201_CREATED
)
def create_airport_endpoint(
    data: AirportCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*airport_managers)),
):
    airport = create_airport(db, data)
    if airport is None:
        raise HTTPException(409, "Airport code already exists")
    return airport


@router.get("/", response_model=list[AirportResponse])
def list_airports_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*airport_managers)),
):
    return list_airports(db, skip, limit)


@router.get("/{airport_id}", response_model=AirportResponse)
def get_airport_endpoint(
    airport_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*airport_managers)),
):
    airport = get_airport(db, airport_id)
    if not airport:
        raise HTTPException(404, "Airport not found")
    return airport


@router.patch("/{airport_id}", response_model=AirportResponse)
def update_airport_endpoint(
    airport_id: UUID,
    data: AirportUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*airport_managers)),
):
    airport = get_airport(db, airport_id)
    if not airport:
        raise HTTPException(404, "Airport not found")

    return update_airport(db, airport, data)


@router.patch("/{airport_id}/deactivate", response_model=AirportResponse)
def deactivate_airport_endpoint(
    airport_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*airport_managers)),
):
    airport = get_airport(db, airport_id)
    if not airport:
        raise HTTPException(404, "Airport not found")

    return deactivate_airport(db, airport)