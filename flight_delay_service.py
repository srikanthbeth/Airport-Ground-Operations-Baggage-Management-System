from datetime import datetime, timezone
from math import ceil
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.constants import (
    FlightDelayStatus,
    FlightStatus,
)
from models.flight import Flight
from models.flight_delay import FlightDelay
from models.user import User
from repositories.flight_delay_repository import FlightDelayRepository


class FlightDelayService:

    @staticmethod
    def _get_flight(db: Session, flight_id: UUID):
        flight = db.query(Flight).filter(
            Flight.id == flight_id
        ).first()

        if not flight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flight not found",
            )

        return flight

    @staticmethod
    def _get_user(db: Session, user_id: UUID):
        user = db.query(User).filter(
            User.id == user_id
        ).first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is inactive",
            )

        return user

    @staticmethod
    def _calculate_delay_minutes(
        original_departure: datetime,
        revised_departure: datetime,
    ) -> int:
        seconds = (
            revised_departure - original_departure
        ).total_seconds()

        return max(0, ceil(seconds / 60))

    @classmethod
    def create(
        cls,
        db: Session,
        payload,
        current_user: User,
    ):
        flight = cls._get_flight(db, payload.flight_id)

        if flight.status in (
            FlightStatus.DEPARTED,
            FlightStatus.ARRIVED,
            FlightStatus.CANCELLED,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A delay cannot be reported for this flight status",
            )

        if payload.revised_departure <= flight.scheduled_departure:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Revised departure must be later than scheduled departure",
            )

        if payload.revised_arrival < flight.scheduled_arrival:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Revised arrival cannot be earlier than scheduled arrival",
            )

        if payload.assigned_to_id:
            cls._get_user(db, payload.assigned_to_id)

        duration = cls._calculate_delay_minutes(
            flight.scheduled_departure,
            payload.revised_departure,
        )

        delay = FlightDelay(
            flight_id=flight.id,
            reported_by_id=current_user.id,
            assigned_to_id=payload.assigned_to_id,
            reason=payload.reason,
            impact=payload.impact,
            description=payload.description,
            original_departure=flight.scheduled_departure,
            revised_departure=payload.revised_departure,
            original_arrival=flight.scheduled_arrival,
            revised_arrival=payload.revised_arrival,
            delay_duration_minutes=duration,
            status=FlightDelayStatus.PENDING,
        )

        return FlightDelayRepository.create(db, delay)

    @staticmethod
    def get(db: Session, delay_id: UUID):
        delay = FlightDelayRepository.get_by_id(db, delay_id)

        if not delay:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Flight delay not found",
            )

        return delay

    @classmethod
    def list(
        cls,
        db: Session,
        flight_id=None,
        status_filter=None,
        reason=None,
        page=1,
        size=10,
    ):
        if flight_id is not None:
            cls._get_flight(db, flight_id)

        items, total = FlightDelayRepository.list(
            db=db,
            flight_id=flight_id,
            status=status_filter,
            reason=reason,
            page=page,
            size=size,
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "size": size,
            "pages": ceil(total / size) if total else 0,
        }

    @classmethod
    def assign(
        cls,
        db: Session,
        delay_id: UUID,
        assigned_to_id: UUID,
    ):
        delay = cls.get(db, delay_id)

        if delay.status in (
            FlightDelayStatus.REJECTED,
            FlightDelayStatus.RESOLVED,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot assign a rejected or resolved delay",
            )

        cls._get_user(db, assigned_to_id)

        delay.assigned_to_id = assigned_to_id
        delay.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(delay)

        return delay

    @classmethod
    def review(
        cls,
        db: Session,
        delay_id: UUID,
        payload,
    ):
        delay = cls.get(db, delay_id)
        flight = cls._get_flight(db, delay.flight_id)

        if delay.status != FlightDelayStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only pending delays can be reviewed",
            )

        if payload.status == FlightDelayStatus.APPROVED:
            delay.status = FlightDelayStatus.APPROVED
            delay.approved_at = datetime.now(timezone.utc)

            if flight.status not in (
                FlightStatus.DEPARTED,
                FlightStatus.ARRIVED,
                FlightStatus.CANCELLED,
            ):
                flight.status = FlightStatus.DELAYED

        elif payload.status == FlightDelayStatus.REJECTED:
            delay.status = FlightDelayStatus.REJECTED

            if not payload.resolution_notes:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Resolution notes are required when rejecting a delay",
                )

            delay.resolution_notes = payload.resolution_notes

        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Review status must be approved or rejected",
            )

        delay.updated_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(delay)

        return delay

    @classmethod
    def resolve(
        cls,
        db: Session,
        delay_id: UUID,
        resolution_notes: str,
    ):
        delay = cls.get(db, delay_id)
        flight = cls._get_flight(db, delay.flight_id)

        if delay.status != FlightDelayStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only approved delays can be resolved",
            )

        if not resolution_notes or not resolution_notes.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Resolution notes are required",
            )

        delay.status = FlightDelayStatus.RESOLVED
        delay.resolution_notes = resolution_notes.strip()
        delay.resolved_at = datetime.now(timezone.utc)
        delay.updated_at = datetime.now(timezone.utc)

        # Restore scheduled status only if the flight has not departed.
        if flight.status == FlightStatus.DELAYED:
            flight.status = FlightStatus.SCHEDULED

        db.commit()
        db.refresh(delay)

        return delay

    @classmethod
    def delete(cls, db: Session, delay_id: UUID):
        delay = cls.get(db, delay_id)

        if delay.status not in (
            FlightDelayStatus.REJECTED,
            FlightDelayStatus.RESOLVED,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Only rejected or resolved delays can be deleted",
            )

        FlightDelayRepository.delete(db, delay)

        return {"message": "Flight delay deleted successfully"}