
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from core.constants import (
    UserRole,
    GroundTaskCategory,
    GroundTaskPriority,
    GroundTaskStatus,
)
from core.permissions import require_roles
from routes.auth import get_current_user
from db.session import get_db
from models.ground_staff import GroundStaff


from schemas.ground_task import (
    GroundTaskCreate,
    GroundTaskUpdate,
    GroundTaskStatusUpdate,
    GroundTaskResponse,
    GroundTaskListResponse,
)
from services.ground_task_service import (
    create_ground_task,
    get_ground_task,
    list_ground_tasks,
    update_ground_task,
    update_ground_task_status,
)


router = APIRouter(
    prefix="/api/v1/ground-tasks",
    tags=["Ground Tasks"],
)


MANAGEMENT_ROLES = (
    UserRole.SUPER_ADMIN,
    UserRole.AIRPORT_OPERATIONS_MANAGER,
    UserRole.GROUND_STAFF_SUPERVISOR,
)


@router.post(
    "/",
    response_model=GroundTaskResponse,
    status_code=201,
)
def create_task(
    payload: GroundTaskCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return create_ground_task(
        db,
        payload.model_dump(),
        current_user,
    )


@router.get("/", response_model=GroundTaskListResponse)
def get_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    ground_staff_id: UUID | None = None,
    airport_id: UUID | None = None,
    status: GroundTaskStatus | None = None,
    category: GroundTaskCategory | None = None,
    priority: GroundTaskPriority | None = None,
    flight_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return list_ground_tasks(
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


@router.get("/{task_id}", response_model=GroundTaskResponse)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return get_ground_task(db, task_id)


@router.patch("/{task_id}", response_model=GroundTaskResponse)
def update_task(
    task_id: UUID,
    payload: GroundTaskUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(*MANAGEMENT_ROLES)),
):
    return update_ground_task(
        db,
        task_id,
        payload.model_dump(exclude_unset=True),
    )


@router.patch(
    "/{task_id}/status",
    response_model=GroundTaskResponse,
)
def change_task_status(
    task_id: UUID,
    payload: GroundTaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role not in MANAGEMENT_ROLES:
        staff = (
            db.query(GroundStaff)
            .filter(GroundStaff.user_id == current_user.id)
            .first()
        )

        if not staff:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authorized")

        task = get_ground_task(db, task_id)

        if task.ground_staff_id != staff.id:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authorized")

    return update_ground_task_status(
        db,
        task_id,
        payload.status,
    )
