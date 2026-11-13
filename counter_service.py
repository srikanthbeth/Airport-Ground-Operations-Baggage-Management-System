from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import CounterStatus, TerminalStatus
from models.checkin_counter import CheckInCounter
from models.terminal import Terminal
from repositories.counter_repository import CounterRepository
from repositories.resource_assignment_repository import (
    ResourceAssignmentRepository,
)


class CounterService:

    @staticmethod
    def get_counter_or_404(db: Session, counter_id: UUID):
        counter = CounterRepository.get(db, counter_id)

        if not counter:
            raise HTTPException(404, "Check-in counter not found")

        return counter

    @staticmethod
    def validate_terminal(db: Session, terminal_id: UUID):
        terminal = db.get(Terminal, terminal_id)

        if not terminal:
            raise HTTPException(404, "Terminal not found")

        if terminal.status != TerminalStatus.ACTIVE:
            raise HTTPException(400, "Terminal is not active")

        return terminal

    @classmethod
    def create(cls, db: Session, data):
        cls.validate_terminal(db, data.terminal_id)

        counter = CheckInCounter(**data.model_dump())

        try:
            return CounterRepository.create(db, counter)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                "Counter number already exists in this terminal",
            )

    @classmethod
    def list(cls, db, terminal_id, skip, limit):
        if terminal_id:
            cls.validate_terminal(db, terminal_id)

        return CounterRepository.list(
            db,
            terminal_id=terminal_id,
            skip=skip,
            limit=limit,
        )

    @classmethod
    def get(cls, db, counter_id):
        return cls.get_counter_or_404(db, counter_id)

    @classmethod
    def update(cls, db, counter_id, data):
        counter = cls.get_counter_or_404(db, counter_id)
        values = data.model_dump(exclude_unset=True)

        if not values:
            raise HTTPException(422, "Provide at least one field to update")

        if "counter_number" in values and values["counter_number"] is None:
            raise HTTPException(422, "Counter number cannot be null")

        if "name" in values and values["name"] is None:
            raise HTTPException(422, "Counter name cannot be null")

        if (
            values.get("status") in (
                CounterStatus.INACTIVE,
                CounterStatus.UNDER_MAINTENANCE,
            )
            and ResourceAssignmentRepository.get_active_for_counter(
                db,
                counter.id,
            )
        ):
            raise HTTPException(
                409,
                "Release the active flight assignment before changing counter status",
            )

        try:
            return CounterRepository.update(db, counter, values)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                "Counter number already exists in this terminal",
            )