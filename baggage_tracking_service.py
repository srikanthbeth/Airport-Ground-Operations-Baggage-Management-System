import math

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import (
    BaggageStatus,
    BaggageTrackingStatus,
)
from models.baggage import Baggage
from models.baggage_tracking import BaggageTracking
from repositories.baggage_tracking_repository import (
    BaggageTrackingRepository,
)


ALLOWED_TRANSITIONS = {
    BaggageTrackingStatus.RECEIVED: {
        BaggageTrackingStatus.SORTED,
        BaggageTrackingStatus.LOST,
        BaggageTrackingStatus.DAMAGED,
    },
    BaggageTrackingStatus.SORTED: {
        BaggageTrackingStatus.LOADED,
        BaggageTrackingStatus.LOST,
        BaggageTrackingStatus.DAMAGED,
    },
    BaggageTrackingStatus.LOADED: {
        BaggageTrackingStatus.IN_TRANSIT,
        BaggageTrackingStatus.LOST,
        BaggageTrackingStatus.DAMAGED,
    },
    BaggageTrackingStatus.IN_TRANSIT: {
        BaggageTrackingStatus.UNLOADED,
        BaggageTrackingStatus.LOST,
        BaggageTrackingStatus.DAMAGED,
    },
    BaggageTrackingStatus.UNLOADED: {
        BaggageTrackingStatus.ARRIVED,
        BaggageTrackingStatus.LOST,
        BaggageTrackingStatus.DAMAGED,
    },
    BaggageTrackingStatus.ARRIVED: {
        BaggageTrackingStatus.CLAIMED,
        BaggageTrackingStatus.LOST,
        BaggageTrackingStatus.DAMAGED,
    },
    BaggageTrackingStatus.CLAIMED: set(),
    BaggageTrackingStatus.LOST: set(),
    BaggageTrackingStatus.DAMAGED: set(),
}


class BaggageTrackingService:

    @staticmethod
    def create_tracking(
        db: Session,
        baggage_id,
        data,
        current_user,
    ):
        baggage = db.get(Baggage, baggage_id)

        if not baggage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Baggage not found",
            )

        if baggage.status == BaggageStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot track cancelled baggage",
            )

        latest = BaggageTrackingRepository.get_latest_by_baggage(
            db,
            baggage_id,
        )

        if latest is None:
            if data.status != BaggageTrackingStatus.RECEIVED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="First tracking status must be RECEIVED",
                )
        elif data.status not in ALLOWED_TRANSITIONS[latest.status]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Invalid baggage tracking transition: "
                    f"{latest.status.value} -> {data.status.value}"
                ),
            )

        tracking = BaggageTracking(
            baggage_id=baggage_id,
            status=data.status,
            location=data.location,
            description=data.description,
            recorded_by=current_user.id,
        )

        return BaggageTrackingRepository.create(db, tracking)

    @staticmethod
    def get_tracking(db: Session, tracking_id):
        tracking = BaggageTrackingRepository.get_by_id(
            db,
            tracking_id,
        )

        if not tracking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Baggage tracking record not found",
            )

        return tracking

    @staticmethod
    def get_latest(db: Session, baggage_id):
        baggage = db.get(Baggage, baggage_id)

        if not baggage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Baggage not found",
            )

        tracking = BaggageTrackingRepository.get_latest_by_baggage(
            db,
            baggage_id,
        )

        if not tracking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tracking history found for this baggage",
            )

        return tracking

    @staticmethod
    def list_tracking(
        db: Session,
        baggage_id,
        page: int = 1,
        page_size: int = 20,
    ):
        baggage = db.get(Baggage, baggage_id)

        if not baggage:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Baggage not found",
            )

        items, total = BaggageTrackingRepository.list_by_baggage(
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