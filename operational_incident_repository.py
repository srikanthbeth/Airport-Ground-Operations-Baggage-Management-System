from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from models.operational_incident import OperationalIncident


class OperationalIncidentRepository:

    @staticmethod
    def create(db: Session, incident: OperationalIncident):
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return incident

    @staticmethod
    def get_by_id(db: Session, incident_id: UUID):
        return db.query(OperationalIncident).filter(
            OperationalIncident.id == incident_id
        ).first()

    @staticmethod
    def get_by_number(db: Session, incident_number: str):
        return db.query(OperationalIncident).filter(
            OperationalIncident.incident_number == incident_number
        ).first()

    @staticmethod
    def list(
        db: Session,
        skip: int = 0,
        limit: int = 20,
        airport_id: UUID | None = None,
        category: str | None = None,
        severity: str | None = None,
        status: str | None = None,
    ):
        query = db.query(OperationalIncident)

        if airport_id:
            query = query.filter(
                OperationalIncident.airport_id == airport_id
            )

        if category:
            query = query.filter(
                OperationalIncident.category == category
            )

        if severity:
            query = query.filter(
                OperationalIncident.severity == severity
            )

        if status:
            query = query.filter(
                OperationalIncident.status == status
            )

        total = query.count()

        items = (
            query.order_by(OperationalIncident.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

        return items, total

    @staticmethod
    def save(db: Session, incident: OperationalIncident):
        db.add(incident)
        db.commit()
        db.refresh(incident)
        return incident

    @staticmethod
    def delete(db: Session, incident: OperationalIncident):
        db.delete(incident)
        db.commit()