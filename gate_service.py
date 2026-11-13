from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.constants import GateStatus, TerminalStatus
from models.gate import Gate
from models.terminal import Terminal
from repositories.gate_repository import GateRepository
from repositories.resource_assignment_repository import (
    ResourceAssignmentRepository,
)


class GateService:

    @staticmethod
    def get_gate_or_404(db: Session, gate_id: UUID):
        gate = GateRepository.get(db, gate_id)

        if not gate:
            raise HTTPException(404, "Gate not found")

        return gate

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

        gate = Gate(**data.model_dump())

        try:
            return GateRepository.create(db, gate)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                "Gate number already exists in this terminal",
            )

    @classmethod
    def list(cls, db, terminal_id, skip, limit):
        if terminal_id:
            cls.validate_terminal(db, terminal_id)

        return GateRepository.list(
            db,
            terminal_id=terminal_id,
            skip=skip,
            limit=limit,
        )

    @classmethod
    def get(cls, db, gate_id):
        return cls.get_gate_or_404(db, gate_id)

    @classmethod
    def update(cls, db, gate_id, data):
        gate = cls.get_gate_or_404(db, gate_id)
        values = data.model_dump(exclude_unset=True)

        if not values:
            raise HTTPException(422, "Provide at least one field to update")

        if "gate_number" in values and values["gate_number"] is None:
            raise HTTPException(422, "Gate number cannot be null")

        if "name" in values and values["name"] is None:
            raise HTTPException(422, "Gate name cannot be null")

        if (
            values.get("status") in (
                GateStatus.INACTIVE,
                GateStatus.UNDER_MAINTENANCE,
            )
            and ResourceAssignmentRepository.get_active_for_gate(db, gate.id)
        ):
            raise HTTPException(
                409,
                "Release the active flight assignment before changing gate status",
            )

        try:
            return GateRepository.update(db, gate, values)
        except IntegrityError:
            db.rollback()
            raise HTTPException(
                409,
                "Gate number already exists in this terminal",
            )