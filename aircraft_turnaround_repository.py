from sqlalchemy.orm import Session

from models.aircraft_turnaround import AircraftTurnaround


class AircraftTurnaroundRepository:

    @staticmethod
    def create(db: Session, data: dict):
        turnaround = AircraftTurnaround(**data)
        db.add(turnaround)
        db.commit()
        db.refresh(turnaround)
        return turnaround

    @staticmethod
    def get_by_id(db: Session, turnaround_id: str):
        return (
            db.query(AircraftTurnaround)
            .filter(AircraftTurnaround.id == turnaround_id)
            .first()
        )

    @staticmethod
    def get_by_number(db: Session, turnaround_number: str):
        return (
            db.query(AircraftTurnaround)
            .filter(AircraftTurnaround.turnaround_number == turnaround_number)
            .first()
        )

    @staticmethod
    def list_turnarounds(
        db: Session,
        airport_id=None,
        flight_id=None,
        status=None,
        page=1,
        page_size=20,
    ):
        query = db.query(AircraftTurnaround)

        if airport_id:
            query = query.filter(AircraftTurnaround.airport_id == airport_id)

        if flight_id:
            query = query.filter(AircraftTurnaround.flight_id == flight_id)

        if status:
            query = query.filter(AircraftTurnaround.status == status)

        total = query.count()

        items = (
            query.order_by(AircraftTurnaround.scheduled_arrival.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return total, items