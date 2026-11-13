from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.baggage_tracking import BaggageTracking


class BaggageTrackingRepository:

    @staticmethod
    def create(db: Session, tracking: BaggageTracking):
        db.add(tracking)
        db.commit()
        db.refresh(tracking)
        return tracking

    @staticmethod
    def get_by_id(db: Session, tracking_id):
        return db.scalar(
            select(BaggageTracking).where(
                BaggageTracking.id == tracking_id
            )
        )

    @staticmethod
    def get_latest_by_baggage(db: Session, baggage_id):
        return db.scalar(
            select(BaggageTracking)
            .where(BaggageTracking.baggage_id == baggage_id)
            .order_by(
                BaggageTracking.created_at.desc(),
                BaggageTracking.id.desc(),
            )
            .limit(1)
        )

    @staticmethod
    def list_by_baggage(
        db: Session,
        baggage_id,
        page: int = 1,
        page_size: int = 20,
    ):
        query = select(BaggageTracking).where(
            BaggageTracking.baggage_id == baggage_id
        )

        total = db.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0

        items = db.scalars(
            query.order_by(
                BaggageTracking.created_at.desc(),
                BaggageTracking.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return items, total