
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.constants import UserRole
from core.permissions import require_roles
from db.session import get_db
from schemas.baggage_screening import (
    BaggageScreeningStart,
    BaggageScreeningComplete,
    BaggageScreeningResponse,
    BaggageScreeningListResponse,
)
from services.baggage_screening_service import (
    BaggageScreeningService,
)


router = APIRouter(
    prefix="/api/v1/baggage-screenings",
    tags=["Baggage Screenings"],
)

screening_roles = require_roles(
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.GROUND_STAFF_SUPERVISOR,
    UserRole.BAGGAGE_HANDLING_STAFF,
)


@router.post(
    "/{baggage_id}/start",
    response_model=BaggageScreeningResponse,
    status_code=201,
)
def start_screening(
    baggage_id: UUID,
    data: BaggageScreeningStart,
    db: Session = Depends(get_db),
    current_user=Depends(screening_roles),
):
    return BaggageScreeningService.start_screening(
        db, baggage_id, data, current_user
    )


@router.patch(
    "/{screening_id}/complete",
    response_model=BaggageScreeningResponse,
)
def complete_screening(
    screening_id: UUID,
    data: BaggageScreeningComplete,
    db: Session = Depends(get_db),
    current_user=Depends(screening_roles),
):
    return BaggageScreeningService.complete_screening(
        db, screening_id, data
    )


@router.get(
    "/{baggage_id}/history",
    response_model=BaggageScreeningListResponse,
)
def get_screening_history(
    baggage_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(screening_roles),
):
    return BaggageScreeningService.get_history(
        db, baggage_id, page, page_size
    )


@router.get(
    "/record/{screening_id}",
    response_model=BaggageScreeningResponse,
)
def get_screening_record(
    screening_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(screening_roles),
):
    return BaggageScreeningService.get_screening(
        db, screening_id
    )
