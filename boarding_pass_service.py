import secrets
import string

from sqlalchemy.orm import Session

from core.constants import BoardingPassStatus
from models.boarding_pass import BoardingPass
from repositories import boarding_pass_repository


def generate_boarding_pass_number():
    alphabet = string.ascii_uppercase + string.digits
    return "BP-" + "".join(secrets.choice(alphabet) for _ in range(12))


def issue_boarding_pass(db: Session, checkin_id):
    existing = boarding_pass_repository.get_boarding_pass_by_checkin(
        db, checkin_id
    )

    if existing:
        return existing

    for _ in range(5):
        number = generate_boarding_pass_number()

        if not boarding_pass_repository.get_boarding_pass_by_number(
            db, number
        ):
            boarding_pass = BoardingPass(
                checkin_id=checkin_id,
                boarding_pass_number=number,
                status=BoardingPassStatus.ACTIVE,
            )

            return boarding_pass_repository.create_boarding_pass(
                db, boarding_pass
            )

    raise ValueError("Could not generate a unique boarding pass number")