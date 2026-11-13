
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.baggage_screening import BaggageScreening


class BaggageScreeningRepository:

    @staticmethod
    def create(db: Session, screening: BaggageScreening):
        db.add(screening)
        db.commit()
        db.refresh(screening)
        return screening

    @staticmethod
    def get_by_id(db: Session, screening_id):
        return db.scalar(
            select(BaggageScreening).where(
                BaggageScreening.id == screening_id
            )
        )

    @staticmethod
    def get_latest_by_baggage(db: Session, baggage_id):
        return db.scalar(
            select(BaggageScreening)
            .where(BaggageScreening.baggage_id == baggage_id)
            .order_by(
                BaggageScreening.started_at.desc(),
                BaggageScreening.id.desc(),
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
        query = select(BaggageScreening).where(
            BaggageScreening.baggage_id == baggage_id
        )

        total = db.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0

        items = db.scalars(
            query.order_by(
                BaggageScreening.started_at.desc(),
                BaggageScreening.id.desc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()

        return items, total
