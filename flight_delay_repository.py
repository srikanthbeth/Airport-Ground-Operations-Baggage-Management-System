from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.flight_delay import FlightDelay
from core.constants import FlightDelayReason, FlightDelayStatus


class FlightDelayRepository:

    @staticmethod
    def create(db: Session, delay: FlightDelay):
        db.add(delay)
        db.commit()
        db.refresh(delay)
        return delay

    @staticmethod
    def get_by_id(db: Session, delay_id: UUID):
        return db.scalar(
            select(FlightDelay).where(FlightDelay.id == delay_id)
        )

    @staticmethod
    def list(
        db: Session,
        flight_id: UUID | None = None,
        status: FlightDelayStatus | None = None,
        reason: FlightDelayReason | None = None,
        page: int = 1,
        size: int = 10,
    ):
        query = select(FlightDelay)
        count_query = select(func.count(FlightDelay.id))

        if flight_id is not None:
            query = query.where(FlightDelay.flight_id == flight_id)
            count_query = count_query.where(
                FlightDelay.flight_id == flight_id
            )

        if status is not None:
            query = query.where(FlightDelay.status == status)
            count_query = count_query.where(
                FlightDelay.status == status
            )

        if reason is not None:
            query = query.where(FlightDelay.reason == reason)
            count_query = count_query.where(
                FlightDelay.reason == reason
            )

        total = db.scalar(count_query) or 0

        items = db.scalars(
            query.order_by(FlightDelay.reported_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        ).all()

        return items, total

    @staticmethod
    def delete(db: Session, delay: FlightDelay):
        db.delete(delay)
        db.commit()