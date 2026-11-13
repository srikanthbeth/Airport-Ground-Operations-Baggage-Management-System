from sqlalchemy.orm import Session

from models.ground_equipment import GroundEquipment, GroundEquipmentUsage


def get_equipment(db: Session, equipment_id):
    return (
        db.query(GroundEquipment)
        .filter(GroundEquipment.id == equipment_id)
        .first()
    )


def get_by_code(db: Session, equipment_code: str):
    return (
        db.query(GroundEquipment)
        .filter(GroundEquipment.equipment_code == equipment_code)
        .first()
    )


def get_by_serial_number(db: Session, serial_number: str):
    return (
        db.query(GroundEquipment)
        .filter(GroundEquipment.serial_number == serial_number)
        .first()
    )


def list_equipment(
    db: Session,
    airport_id=None,
    equipment_type=None,
    status=None,
    assigned_flight_id=None,
    page: int = 1,
    page_size: int = 10,
):
    query = db.query(GroundEquipment)

    if airport_id:
        query = query.filter(GroundEquipment.airport_id == airport_id)

    if equipment_type:
        query = query.filter(GroundEquipment.equipment_type == equipment_type)

    if status:
        query = query.filter(GroundEquipment.status == status)

    if assigned_flight_id:
        query = query.filter(
            GroundEquipment.assigned_flight_id == assigned_flight_id
        )

    total = query.count()

    items = (
        query.order_by(GroundEquipment.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return total, items


def create_equipment(db: Session, equipment: GroundEquipment):
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def save_equipment(db: Session, equipment: GroundEquipment):
    db.add(equipment)
    db.commit()
    db.refresh(equipment)
    return equipment


def delete_equipment(db: Session, equipment: GroundEquipment):
    db.delete(equipment)
    db.commit()


def create_usage(db: Session, usage: GroundEquipmentUsage):
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


def list_usage(db: Session, equipment_id):
    return (
        db.query(GroundEquipmentUsage)
        .filter(GroundEquipmentUsage.equipment_id == equipment_id)
        .order_by(GroundEquipmentUsage.started_at.desc())
        .all()
    )