
import math
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import (
    BaggageScreeningStatus,
    BaggageStatus,
)
from models.baggage import Baggage
from models.baggage_screening import BaggageScreening
from repositories.baggage_screening_repository import (
    BaggageScreeningRepository,
)


class BaggageScreeningService:

    @staticmethod
    def start_screening(
        db: Session,
        baggage_id,
        data,
        current_user,
    ):
        baggage = db.get(Baggage, baggage_id)

        if not baggage:
            raise HTTPException(
                status_code=404,
                detail="Baggage not found",
            )

        if baggage.status != BaggageStatus.REGISTERED:
            raise HTTPException(
                status_code=400,
                detail="Only registered baggage can be screened",
            )

        latest = (
            BaggageScreeningRepository.get_latest_by_baggage(
                db, baggage_id
            )
        )

        if latest:
            if latest.status == BaggageScreeningStatus.IN_PROGRESS:
                raise HTTPException(
                    status_code=409,
                    detail="Screening is already in progress",
                )

            if latest.status in (
                BaggageScreeningStatus.CLEARED,
                BaggageScreeningStatus.REJECTED,
            ):
                raise HTTPException(
                    status_code=409,
                    detail="Screening is already completed",
                )

        screening = BaggageScreening(
            baggage_id=baggage_id,
            screening_method=data.screening_method,
            status=BaggageScreeningStatus.IN_PROGRESS,
            notes=data.notes,
            screened_by=current_user.id,
        )

        return BaggageScreeningRepository.create(db, screening)

    @staticmethod
    def complete_screening(
        db: Session,
        screening_id,
        data,
    ):
        screening = BaggageScreeningRepository.get_by_id(
            db, screening_id
        )

        if not screening:
            raise HTTPException(
                status_code=404,
                detail="Screening record not found",
            )

        if screening.status != BaggageScreeningStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=409,
                detail="Only an in-progress screening can be completed",
            )

        if data.status == BaggageScreeningStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=400,
                detail="Completion status must be a final screening status",
            )

        screening.status = data.status

        if data.notes:
            screening.notes = (
                f"{screening.notes}\n{data.notes}"
                if screening.notes
                else data.notes
            )

        screening.completed_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(screening)

        return screening

    @staticmethod
    def get_screening(db: Session, screening_id):
        screening = BaggageScreeningRepository.get_by_id(
            db, screening_id
        )

        if not screening:
            raise HTTPException(
                status_code=404,
                detail="Screening record not found",
            )

        return screening

    @staticmethod
    def get_history(
        db: Session,
        baggage_id,
        page: int = 1,
        page_size: int = 20,
    ):
        if not db.get(Baggage, baggage_id):
            raise HTTPException(
                status_code=404,
                detail="Baggage not found",
            )

        items, total = BaggageScreeningRepository.list_by_baggage(
            db,
            baggage_id,
            page,
            page_size,
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": math.ceil(total / page_size) if total else 0,
        }
