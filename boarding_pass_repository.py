from uuid import UUID

from sqlalchemy.orm import Session

from models.boarding_pass import BoardingPass


def create_boarding_pass(db: Session, boarding_pass: BoardingPass):
    db.add(boarding_pass)
    db.flush()
    return boarding_pass


def get_boarding_pass_by_id(db: Session, boarding_pass_id: UUID):
    return (
        db.query(BoardingPass)
        .filter(BoardingPass.id == boarding_pass_id)
        .first()
    )


def get_boarding_pass_by_number(db: Session, number: str):
    return (
        db.query(BoardingPass)
        .filter(BoardingPass.boarding_pass_number == number)
        .first()
    )


def get_boarding_pass_by_checkin(db: Session, checkin_id: UUID):
    return (
        db.query(BoardingPass)
        .filter(BoardingPass.checkin_id == checkin_id)
        .first()
    )