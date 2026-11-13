from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.checkin_counter import CheckInCounter


class CounterRepository:

    @staticmethod
    def create(db: Session, counter: CheckInCounter):
        db.add(counter)
        db.commit()
        db.refresh(counter)
        return counter

    @staticmethod
    def get(db: Session, counter_id: UUID):
        return db.scalar(
            select(CheckInCounter).where(
                CheckInCounter.id == counter_id
            )
        )

    @staticmethod
    def list(
        db: Session,
        terminal_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        query = select(CheckInCounter)

        if terminal_id:
            query = query.where(
                CheckInCounter.terminal_id == terminal_id
            )

        query = (
            query.order_by(CheckInCounter.counter_number)
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(query).all())

    @staticmethod
    def update(db: Session, counter: CheckInCounter, values: dict):
        for key, value in values.items():
            setattr(counter, key, value)

        db.commit()
        db.refresh(counter)
        return counter