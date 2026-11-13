
from sqlalchemy.orm import Session

from models.ground_task import GroundTask


class GroundTaskRepository:

    @staticmethod
    def create(db: Session, data: dict) -> GroundTask:
        task = GroundTask(**data)
        db.add(task)
        db.commit()
        db.refresh(task)
        return task

    @staticmethod
    def get_by_id(db: Session, task_id):
        return (
            db.query(GroundTask)
            .filter(GroundTask.id == task_id)
            .first()
        )

    @staticmethod
    def get_by_number(db: Session, task_number: str):
        return (
            db.query(GroundTask)
            .filter(GroundTask.task_number == task_number)
            .first()
        )

    @staticmethod
    def list_tasks(
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
        query = db.query(GroundTask)

        if ground_staff_id:
            query = query.filter(
                GroundTask.ground_staff_id == ground_staff_id
            )

        if airport_id:
            query = query.filter(GroundTask.airport_id == airport_id)

        if status:
            query = query.filter(GroundTask.status == status)

        if category:
            query = query.filter(GroundTask.category == category)

        if priority:
            query = query.filter(GroundTask.priority == priority)

        if flight_id:
            query = query.filter(GroundTask.flight_id == flight_id)

        total = query.count()

        items = (
            query.order_by(GroundTask.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items

    @staticmethod
    def update(db: Session, task: GroundTask, data: dict):
        for key, value in data.items():
            setattr(task, key, value)

        db.commit()
        db.refresh(task)
        return task
