from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.gate import Gate


class GateRepository:

    @staticmethod
    def create(db: Session, gate: Gate):
        db.add(gate)
        db.commit()
        db.refresh(gate)
        return gate

    @staticmethod
    def get(db: Session, gate_id: UUID):
        return db.scalar(
            select(Gate).where(Gate.id == gate_id)
        )

    @staticmethod
    def list(
        db: Session,
        terminal_id: UUID | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        query = select(Gate)

        if terminal_id:
            query = query.where(Gate.terminal_id == terminal_id)

        query = (
            query.order_by(Gate.gate_number)
            .offset(skip)
            .limit(limit)
        )

        return list(db.scalars(query).all())

    @staticmethod
    def update(db: Session, gate: Gate, values: dict):
        for key, value in values.items():
            setattr(gate, key, value)

        db.commit()
        db.refresh(gate)
        return gate