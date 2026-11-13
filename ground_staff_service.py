
import math

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.ground_staff import GroundStaff
from models.user import User
from models.airport import Airport
from models.terminal import Terminal

from core.constants import (
    UserRole,
    GroundStaffStatus,
)

from repositories.ground_staff_repository import (
    GroundStaffRepository,
)


ALLOWED_STAFF_ROLES = {
    UserRole.GROUND_STAFF_SUPERVISOR,
    UserRole.BAGGAGE_HANDLING_STAFF,
    UserRole.CHECK_IN_AGENT,
    UserRole.GATE_AGENT,
    UserRole.MAINTENANCE_STAFF,
}


def validate_airport_and_terminal(
    db: Session,
    airport_id,
    terminal_id=None,
):
    airport = (
        db.query(Airport)
        .filter(Airport.id == airport_id)
        .first()
    )

    if not airport:
        raise HTTPException(
            status_code=404,
            detail="Airport not found",
        )

    if terminal_id is not None:
        terminal = (
            db.query(Terminal)
            .filter(Terminal.id == terminal_id)
            .first()
        )

        if not terminal:
            raise HTTPException(
                status_code=404,
                detail="Terminal not found",
            )

        if terminal.airport_id != airport_id:
            raise HTTPException(
                status_code=400,
                detail="Terminal does not belong to the selected airport",
            )


def create_ground_staff(db: Session, data):
    user = (
        db.query(User)
        .filter(User.id == data.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive users cannot be assigned as ground staff",
        )

    if user.role not in ALLOWED_STAFF_ROLES:
        raise HTTPException(
            status_code=400,
            detail="User role is not eligible for ground staff registration",
        )

    if GroundStaffRepository.get_by_user_id(db, data.user_id):
        raise HTTPException(
            status_code=409,
            detail="Ground staff profile already exists for this user",
        )

    if GroundStaffRepository.get_by_employee_number(
        db,
        data.employee_number,
    ):
        raise HTTPException(
            status_code=409,
            detail="Employee number already exists",
        )

    validate_airport_and_terminal(
        db,
        data.airport_id,
        data.terminal_id,
    )

    staff = GroundStaff(
        user_id=data.user_id,
        employee_number=data.employee_number,
        department=data.department,
        designation=data.designation,
        phone=data.phone,
        shift=data.shift,
        airport_id=data.airport_id,
        terminal_id=data.terminal_id,
        date_of_joining=data.date_of_joining,
    )

    return GroundStaffRepository.create(db, staff)


def get_ground_staff(db: Session, staff_id):
    staff = GroundStaffRepository.get_by_id(db, staff_id)

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Ground staff record not found",
        )

    return staff


def list_ground_staff(
    db: Session,
    page=1,
    page_size=10,
    department=None,
    shift=None,
    status=None,
    airport_id=None,
):
    items, total = GroundStaffRepository.list_staff(
        db=db,
        page=page,
        page_size=page_size,
        department=department,
        shift=shift,
        status=status,
        airport_id=airport_id,
    )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": math.ceil(total / page_size) if total else 0,
    }


def update_ground_staff(db: Session, staff_id, data):
    staff = get_ground_staff(db, staff_id)

    updates = data.model_dump(exclude_unset=True)

    # Null is permitted only for the optional terminal assignment.
    updates = {
        key: value
        for key, value in updates.items()
        if value is not None or key == "terminal_id"
    }

    if "employee_number" in updates:
        existing = GroundStaffRepository.get_by_employee_number(
            db,
            updates["employee_number"],
        )

        if existing and existing.id != staff.id:
            raise HTTPException(
                status_code=409,
                detail="Employee number already exists",
            )

    new_airport_id = updates.get("airport_id", staff.airport_id)
    new_terminal_id = updates.get("terminal_id", staff.terminal_id)

    validate_airport_and_terminal(
        db,
        new_airport_id,
        new_terminal_id,
    )

    for key, value in updates.items():
        setattr(staff, key, value)

    return GroundStaffRepository.update(db, staff)
