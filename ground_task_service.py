
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import GroundTaskStatus, GroundStaffStatus
from models.ground_task import GroundTask
from models.ground_staff import GroundStaff
from models.airport import Airport
from models.terminal import Terminal
from models.flight import Flight
from repositories.ground_task_repository import GroundTaskRepository


ALLOWED_TRANSITIONS = {
    GroundTaskStatus.ASSIGNED: {
        GroundTaskStatus.IN_PROGRESS,
        GroundTaskStatus.CANCELLED,
    },
    GroundTaskStatus.IN_PROGRESS: {
        GroundTaskStatus.BLOCKED,
        GroundTaskStatus.COMPLETED,
        GroundTaskStatus.CANCELLED,
    },
    GroundTaskStatus.BLOCKED: {
        GroundTaskStatus.IN_PROGRESS,
        GroundTaskStatus.CANCELLED,
    },
    GroundTaskStatus.COMPLETED: set(),
    GroundTaskStatus.CANCELLED: set(),
}

def validate_task_references(
    db: Session,
    ground_staff_id,
    airport_id,
    terminal_id=None,
    flight_id=None,
):
    # 1. Validate airport first
    airport = db.query(Airport).filter(
        Airport.id == airport_id
    ).first()

    if not airport:
        raise HTTPException(
            status_code=404,
            detail="Airport not found",
        )

    # 2. Validate ground staff
    staff = db.query(GroundStaff).filter(
        GroundStaff.id == ground_staff_id
    ).first()

    if not staff:
        raise HTTPException(
            status_code=404,
            detail="Ground staff not found",
        )

    if staff.status != GroundStaffStatus.ACTIVE:
        raise HTTPException(
            status_code=400,
            detail="Ground staff is not active",
        )

    # 3. Validate airport assignment
    if staff.airport_id != airport_id:
        raise HTTPException(
            status_code=400,
            detail="Ground staff does not belong to this airport",
        )

    # 4. Validate terminal
    if terminal_id:
        terminal = db.query(Terminal).filter(
            Terminal.id == terminal_id
        ).first()

        if not terminal:
            raise HTTPException(
                status_code=404,
                detail="Terminal not found",
            )

        if terminal.airport_id != airport_id:
            raise HTTPException(
                status_code=400,
                detail="Terminal does not belong to this airport",
            )

        if staff.terminal_id and staff.terminal_id != terminal_id:
            raise HTTPException(
                status_code=400,
                detail="Ground staff is not assigned to this terminal",
            )

    # 5. Validate flight
    if flight_id:
        flight = db.query(Flight).filter(
            Flight.id == flight_id
        ).first()

        if not flight:
            raise HTTPException(
                status_code=404,
                detail="Flight not found",
            )

        if flight.airport_id != airport_id:
            raise HTTPException(
                status_code=400,
                detail="Flight does not belong to this airport",
            )

def create_ground_task(db: Session, data: dict, current_user):
    if GroundTaskRepository.get_by_number(db, data["task_number"]):
        raise HTTPException(
            status_code=409,
            detail="Task number already exists",
        )

    validate_task_references(
        db,
        ground_staff_id=data["ground_staff_id"],
        airport_id=data["airport_id"],
        terminal_id=data.get("terminal_id"),
        flight_id=data.get("flight_id"),
    )

    if (
        data.get("scheduled_start")
        and data.get("scheduled_end")
        and data["scheduled_end"] <= data["scheduled_start"]
    ):
        raise HTTPException(
            status_code=400,
            detail="Scheduled end must be after scheduled start",
        )

    data["created_by"] = current_user.id

    return GroundTaskRepository.create(db, data)


def get_ground_task(db: Session, task_id: UUID):
    task = GroundTaskRepository.get_by_id(db, task_id)

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Ground task not found",
        )

    return task


def list_ground_tasks(
    db: Session,
    page: int = 1,
    page_size: int = 10,
    ground_staff_id=None,
    airport_id=None,
    status=None,
    category=None,
    priority=None,
    flight_id=None,
):
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid pagination parameters",
        )

    total, items = GroundTaskRepository.list_tasks(
        db=db,
        page=page,
        page_size=page_size,
        ground_staff_id=ground_staff_id,
        airport_id=airport_id,
        status=status,
        category=category,
        priority=priority,
        flight_id=flight_id,
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def update_ground_task(db: Session, task_id: UUID, data: dict):
    task = get_ground_task(db, task_id)

    if task.status in {
        GroundTaskStatus.COMPLETED,
        GroundTaskStatus.CANCELLED,
    }:
        raise HTTPException(
            status_code=400,
            detail="Completed or cancelled tasks cannot be edited",
        )

    if "task_number" in data and data["task_number"] != task.task_number:
        existing = GroundTaskRepository.get_by_number(
            db, data["task_number"]
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail="Task number already exists",
            )

    ground_staff_id = data.get("ground_staff_id", task.ground_staff_id)
    airport_id = data.get("airport_id", task.airport_id)
    terminal_id = data.get("terminal_id", task.terminal_id)
    flight_id = data.get("flight_id", task.flight_id)

    validate_task_references(
        db,
        ground_staff_id=ground_staff_id,
        airport_id=airport_id,
        terminal_id=terminal_id,
        flight_id=flight_id,
    )

    scheduled_start = data.get("scheduled_start", task.scheduled_start)
    scheduled_end = data.get("scheduled_end", task.scheduled_end)

    if (
        scheduled_start
        and scheduled_end
        and scheduled_end <= scheduled_start
    ):
        raise HTTPException(
            status_code=400,
            detail="Scheduled end must be after scheduled start",
        )

    return GroundTaskRepository.update(db, task, data)


def update_ground_task_status(
    db: Session,
    task_id: UUID,
    new_status: GroundTaskStatus,
):
    task = get_ground_task(db, task_id)

    allowed = ALLOWED_TRANSITIONS.get(task.status, set())

    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Cannot change task status from "
                f"{task.status.value} to {new_status.value}"
            ),
        )

    now = datetime.now(timezone.utc)

    if new_status == GroundTaskStatus.IN_PROGRESS and task.started_at is None:
        task.started_at = now

    if new_status == GroundTaskStatus.COMPLETED:
        task.completed_at = now

    task.status = new_status

    db.commit()
    db.refresh(task)

    return task
