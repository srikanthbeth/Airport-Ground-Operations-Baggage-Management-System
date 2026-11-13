import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from models.airport import Airport
from models.flight import Flight
from models.ground_equipment import GroundEquipment, GroundEquipmentUsage
from core.constants import GroundEquipmentStatus

from repositories import ground_equipment_repository as repository


def normalize_uuid(value):
    if value is None:
        return None

    if isinstance(value, uuid.UUID):
        return value

    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=422, detail="Invalid UUID")


def validate_airport(db: Session, airport_id):
    airport_id = normalize_uuid(airport_id)

    airport = db.query(Airport).filter(Airport.id == airport_id).first()

    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")

    return airport


def validate_flight(db: Session, flight_id):
    if flight_id is None:
        return None

    flight_id = normalize_uuid(flight_id)
    flight = db.query(Flight).filter(Flight.id == flight_id).first()

    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found")

    return flight


def get_equipment_or_404(db: Session, equipment_id):
    equipment = repository.get_equipment(db, normalize_uuid(equipment_id))

    if not equipment:
        raise HTTPException(status_code=404, detail="Ground equipment not found")

    return equipment


def create_equipment(db: Session, data, user):
    validate_airport(db, data.airport_id)

    if data.assigned_flight_id:
        validate_flight(db, data.assigned_flight_id)

    if repository.get_by_code(db, data.equipment_code):
        raise HTTPException(
            status_code=409,
            detail="Equipment code already exists",
        )

    if data.serial_number and repository.get_by_serial_number(
        db, data.serial_number
    ):
        raise HTTPException(
            status_code=409,
            detail="Serial number already exists",
        )

    if data.assigned_flight_id and data.status != GroundEquipmentStatus.IN_USE:
        raise HTTPException(
            status_code=400,
            detail="Equipment assigned to a flight must have IN_USE status",
        )

    equipment = GroundEquipment(
        **data.model_dump(),
        created_by=user.id,
    )

    return repository.create_equipment(db, equipment)


def list_equipment(
    db: Session,
    airport_id=None,
    equipment_type=None,
    status=None,
    assigned_flight_id=None,
    page=1,
    page_size=10,
):
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=422,
            detail="Invalid pagination values",
        )

    total, items = repository.list_equipment(
        db=db,
        airport_id=normalize_uuid(airport_id) if airport_id else None,
        equipment_type=equipment_type,
        status=status,
        assigned_flight_id=(
            normalize_uuid(assigned_flight_id)
            if assigned_flight_id else None
        ),
        page=page,
        page_size=page_size,
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }


def get_equipment(db: Session, equipment_id):
    return get_equipment_or_404(db, equipment_id)


def update_equipment(db: Session, equipment_id, data):
    equipment = get_equipment_or_404(db, equipment_id)
    updates = data.model_dump(exclude_unset=True)

    if "equipment_code" in updates:
        existing = repository.get_by_code(db, updates["equipment_code"])
        if existing and existing.id != equipment.id:
            raise HTTPException(
                status_code=409,
                detail="Equipment code already exists",
            )

    if "serial_number" in updates and updates["serial_number"]:
        existing = repository.get_by_serial_number(
            db, updates["serial_number"]
        )
        if existing and existing.id != equipment.id:
            raise HTTPException(
                status_code=409,
                detail="Serial number already exists",
            )

    if "airport_id" in updates and updates["airport_id"] is not None:
        validate_airport(db, updates["airport_id"])

    if "assigned_flight_id" in updates:
        if updates["assigned_flight_id"] is not None:
            validate_flight(db, updates["assigned_flight_id"])
            if equipment.status != GroundEquipmentStatus.AVAILABLE:
                raise HTTPException(
                    status_code=409,
                    detail="Only available equipment can be assigned",
                )
            equipment.status = GroundEquipmentStatus.IN_USE

    if "last_maintenance_at" in updates and "next_maintenance_at" not in updates:
        if (
            updates["last_maintenance_at"]
            and equipment.next_maintenance_at
            and equipment.next_maintenance_at < updates["last_maintenance_at"]
        ):
            raise HTTPException(
                status_code=400,
                detail="Next maintenance date cannot be earlier than last maintenance date",
            )

    for field, value in updates.items():
        setattr(equipment, field, value)

    return repository.save_equipment(db, equipment)


def update_status(db: Session, equipment_id, new_status):
    equipment = get_equipment_or_404(db, equipment_id)
    current = equipment.status

    allowed_transitions = {
        GroundEquipmentStatus.AVAILABLE: {
            GroundEquipmentStatus.IN_USE,
            GroundEquipmentStatus.MAINTENANCE,
            GroundEquipmentStatus.OUT_OF_SERVICE,
        },
        GroundEquipmentStatus.IN_USE: {
            GroundEquipmentStatus.AVAILABLE,
            GroundEquipmentStatus.OUT_OF_SERVICE,
        },
        GroundEquipmentStatus.MAINTENANCE: {
            GroundEquipmentStatus.AVAILABLE,
            GroundEquipmentStatus.OUT_OF_SERVICE,
        },
        GroundEquipmentStatus.OUT_OF_SERVICE: {
            GroundEquipmentStatus.MAINTENANCE,
            GroundEquipmentStatus.AVAILABLE,
        },
    }

    if new_status == current:
        return equipment

    if new_status not in allowed_transitions[current]:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot change equipment status from {current.value} to {new_status.value}",
        )

    if new_status == GroundEquipmentStatus.AVAILABLE:
        equipment.assigned_flight_id = None

    if new_status == GroundEquipmentStatus.MAINTENANCE:
        equipment.assigned_flight_id = None

    if new_status == GroundEquipmentStatus.OUT_OF_SERVICE:
        equipment.assigned_flight_id = None

    equipment.status = new_status
    return repository.save_equipment(db, equipment)


def record_usage(db: Session, equipment_id, data, user):
    equipment = get_equipment_or_404(db, equipment_id)

    if equipment.status != GroundEquipmentStatus.AVAILABLE:
        raise HTTPException(
            status_code=409,
            detail="Only available equipment can have a usage record",
        )

    if data.flight_id:
        validate_flight(db, data.flight_id)

    usage = GroundEquipmentUsage(
        equipment_id=equipment.id,
        flight_id=data.flight_id,
        used_by=user.id,
        started_at=data.started_at,
        ended_at=data.ended_at,
        notes=data.notes,
    )

    equipment.last_used_at = data.ended_at

    db.add(usage)
    db.add(equipment)
    db.commit()
    db.refresh(usage)

    return usage


def get_usage_history(db: Session, equipment_id):
    equipment = get_equipment_or_404(db, equipment_id)
    return repository.list_usage(db, equipment.id)


def delete_equipment(db: Session, equipment_id):
    equipment = get_equipment_or_404(db, equipment_id)

    if equipment.status == GroundEquipmentStatus.IN_USE:
        raise HTTPException(
            status_code=409,
            detail="Equipment currently in use cannot be deleted",
        )

    repository.delete_equipment(db, equipment)