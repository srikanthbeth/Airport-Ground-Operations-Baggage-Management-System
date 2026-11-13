from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.constants import UserRole
from core.permissions import require_roles
from db.session import get_db
from repositories import boarding_pass_repository
from schemas.boarding_pass import BoardingPassResponse

router = APIRouter(
    prefix="/api/v1/boarding-passes",
    tags=["Boarding Passes"],
)

BOARDING_PASS_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.CHECK_IN_AGENT,
    UserRole.GATE_AGENT,
)


@router.get(
    "/number/{boarding_pass_number}",
    response_model=BoardingPassResponse,
)
def get_boarding_pass_by_number(
    boarding_pass_number: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*BOARDING_PASS_ROLES)),
):
    boarding_pass = boarding_pass_repository.get_boarding_pass_by_number(
        db, boarding_pass_number
    )

    if not boarding_pass:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Boarding pass not found")

    return boarding_pass


@router.get(
    "/checkin/{checkin_id}",
    response_model=BoardingPassResponse,
)
def get_boarding_pass_by_checkin(
    checkin_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*BOARDING_PASS_ROLES)),
):
    boarding_pass = boarding_pass_repository.get_boarding_pass_by_checkin(
        db, checkin_id
    )

    if not boarding_pass:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Boarding pass not found")

    return boarding_pass