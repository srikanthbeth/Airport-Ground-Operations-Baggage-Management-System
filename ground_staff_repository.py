
from sqlalchemy.orm import Session

from models.ground_staff import GroundStaff
from core.constants import (
    GroundStaffDepartment,
    GroundStaffShift,
    GroundStaffStatus,
)


class GroundStaffRepository:

    @staticmethod
    def create(db: Session, staff: GroundStaff):
        db.add(staff)
        db.commit()
        db.refresh(staff)
        return staff

    @staticmethod
    def get_by_id(db: Session, staff_id):
        return (
            db.query(GroundStaff)
            .filter(GroundStaff.id == staff_id)
            .first()
        )

    @staticmethod
    def get_by_user_id(db: Session, user_id):
        return (
            db.query(GroundStaff)
            .filter(GroundStaff.user_id == user_id)
            .first()
        )

    @staticmethod
    def get_by_employee_number(db: Session, employee_number):
        return (
            db.query(GroundStaff)
            .filter(
                GroundStaff.employee_number == employee_number
            )
            .first()
        )

    @staticmethod
    def list_staff(
        db: Session,
        page=1,
        page_size=10,
        department=None,
        shift=None,
        status=None,
        airport_id=None,
    ):
        query = db.query(GroundStaff)

        if department is not None:
            query = query.filter(
                GroundStaff.department == department
            )

        if shift is not None:
            query = query.filter(
                GroundStaff.shift == shift
            )

        if status is not None:
            query = query.filter(
                GroundStaff.status == status
            )

        if airport_id is not None:
            query = query.filter(
                GroundStaff.airport_id == airport_id
            )

        total = query.count()

        items = (
            query.order_by(GroundStaff.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return items, total

    @staticmethod
    def update(db: Session, staff: GroundStaff):
        db.commit()
        db.refresh(staff)
        return staff
