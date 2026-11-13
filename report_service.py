
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy.orm import Session

import models


# ---------------------------------------------------------
# REPORT CONFIGURATION
# ---------------------------------------------------------

REPORT_TYPES = {
    "daily-flight-operations",
    "monthly-flight-performance",
    "baggage-handling",
    "missing-baggage",
    "ground-staff-performance",
    "equipment-utilization",
    "flight-delay-analysis",
    "aircraft-turnaround",
}


# ---------------------------------------------------------
# COMMON HELPERS
# ---------------------------------------------------------

def _get_model(*names):
    """
    Find a model exported by the models package.

    Multiple candidate names are accepted because model naming
    can differ between project implementations.
    """
    for name in names:
        model = getattr(models, name, None)

        if model is not None:
            return model

    raise RuntimeError(
        f"Model not found. Expected one of: {', '.join(names)}. "
        "Check models/__init__.py."
    )


def _get_attr(obj, *names, default=None):
    """Return the first available attribute from an object."""
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)

    return default


def _get_column(model, *names):
    """Return the first available SQLAlchemy model column."""
    for name in names:
        column = getattr(model, name, None)

        if column is not None:
            return column

    raise RuntimeError(
        f"Column not found on {model.__name__}: {', '.join(names)}"
    )


def _value(value):
    """Convert enum values into JSON/CSV-friendly values."""
    if value is None:
        return None

    return getattr(value, "value", value)


def _iso(value):
    if value is None:
        return None

    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(value)


def _date_filter(query, column, date_from=None, date_to=None):
    """Apply inclusive date-range filtering."""
    if date_from:
        query = query.filter(
            column >= datetime.combine(date_from, time.min)
        )

    if date_to:
        query = query.filter(
            column < datetime.combine(
                date_to + timedelta(days=1),
                time.min,
            )
        )

    return query


def _validate_dates(date_from=None, date_to=None):
    if date_from and date_to and date_from > date_to:
        raise ValueError(
            "date_from cannot be later than date_to"
        )


def _sort_and_paginate(
    items: list[dict[str, Any]],
    page: int,
    page_size: int,
    sort_by: str,
    sort_order: str,
):
    if page < 1:
        raise ValueError("page must be greater than or equal to 1")

    if page_size < 1 or page_size > 100:
        raise ValueError("page_size must be between 1 and 100")

    if sort_order not in {"asc", "desc"}:
        raise ValueError("sort_order must be asc or desc")

    total = len(items)

    if not items:
        return total, []

    if sort_by not in items[0]:
        if sort_by == "flight_number":
            sort_by = next(iter(items[0]))
        else:
            raise ValueError(
                f"Invalid sort field '{sort_by}'. "
                f"Available fields: {', '.join(items[0].keys())}"
            )

    def sort_key(item):
        value = item.get(sort_by)

        if value is None:
            return (1, "")

        if isinstance(value, (int, float)):
            return (0, value)

        return (0, str(value).lower())

    items.sort(
        key=sort_key,
        reverse=(sort_order == "desc"),
    )

    start = (page - 1) * page_size

    return total, items[start:start + page_size]


# ---------------------------------------------------------
# FLIGHT REPORT HELPERS
# ---------------------------------------------------------

def _flight_rows(
    db: Session,
    date_from=None,
    date_to=None,
    delayed_only=False,
):
    Flight = _get_model("Flight")

    query = db.query(Flight)

    scheduled_departure = _get_column(
        Flight,
        "scheduled_departure",
    )

    query = _date_filter(
        query,
        scheduled_departure,
        date_from,
        date_to,
    )

    if delayed_only:
        status_column = _get_column(Flight, "status")

        actual_departure = _get_column(
            Flight,
            "actual_departure",
        )

        query = query.filter(
            (status_column == "delayed")
            | (
                actual_departure.isnot(None)
                & scheduled_departure.isnot(None)
                & (actual_departure > scheduled_departure)
            )
        )

    return query.all()


def _daily_flight_operations(db, date_from=None, date_to=None):
    flights = _flight_rows(db, date_from, date_to)

    rows = []

    for flight in flights:
        rows.append({
            "flight_id": str(flight.id),
            "flight_number": flight.flight_number,
            "airline": flight.airline,
            "flight_type": _value(
                _get_attr(flight, "flight_type")
            ),
            "scheduled_departure": _iso(
                _get_attr(flight, "scheduled_departure")
            ),
            "scheduled_arrival": _iso(
                _get_attr(flight, "scheduled_arrival")
            ),
            "actual_departure": _iso(
                _get_attr(flight, "actual_departure")
            ),
            "actual_arrival": _iso(
                _get_attr(flight, "actual_arrival")
            ),
            "status": _value(
                _get_attr(flight, "status")
            ),
        })

    return rows


def _monthly_flight_performance(db, date_from=None, date_to=None):
    flights = _flight_rows(db, date_from, date_to)

    grouped = defaultdict(lambda: {
        "month": None,
        "total_flights": 0,
        "scheduled": 0,
        "delayed": 0,
        "cancelled": 0,
        "departed": 0,
        "arrived": 0,
    })

    for flight in flights:
        scheduled = _get_attr(flight, "scheduled_departure")

        if not scheduled:
            continue

        month = scheduled.strftime("%Y-%m")

        row = grouped[month]
        row["month"] = month
        row["total_flights"] += 1

        status = str(
            _value(_get_attr(flight, "status", default=""))
        ).lower()

        if status == "scheduled":
            row["scheduled"] += 1
        elif status == "delayed":
            row["delayed"] += 1
        elif status == "cancelled":
            row["cancelled"] += 1
        elif status == "departed":
            row["departed"] += 1
        elif status == "arrived":
            row["arrived"] += 1

    return list(grouped.values())


# ---------------------------------------------------------
# BAGGAGE REPORTS
# ---------------------------------------------------------

def _baggage_rows(
    db: Session,
    date_from=None,
    date_to=None,
    missing_only=False,
):
    Baggage = _get_model("Baggage")
    BaggageTracking = _get_model("BaggageTracking")

    baggage_query = db.query(Baggage)

    registered_column = _get_column(
        Baggage,
        "registered_at",
    )

    baggage_query = _date_filter(
        baggage_query,
        registered_column,
        date_from,
        date_to,
    )

    baggage_items = baggage_query.all()

    tracking_query = db.query(BaggageTracking)

    tracking_created = _get_column(
        BaggageTracking,
        "created_at",
    )

    tracking_query = tracking_query.order_by(
        tracking_created.desc()
    )

    tracking_items = tracking_query.all()

    latest_tracking = {}
    lost_ids = set()

    for tracking in tracking_items:
        baggage_id = str(tracking.baggage_id)

        tracking_status = str(
            _value(_get_attr(tracking, "status", default=""))
        ).lower()

        if tracking_status == "lost":
            lost_ids.add(baggage_id)

        if baggage_id not in latest_tracking:
            latest_tracking[baggage_id] = tracking

    rows = []

    for baggage in baggage_items:
        baggage_id = str(baggage.id)

        if missing_only and baggage_id not in lost_ids:
            continue

        tracking = latest_tracking.get(baggage_id)

        rows.append({
            "baggage_id": baggage_id,
            "baggage_tag": _get_attr(
                baggage,
                "baggage_tag",
            ),
            "flight_id": (
                str(baggage.flight_id)
                if _get_attr(baggage, "flight_id")
                else None
            ),
            "baggage_status": _value(
                _get_attr(baggage, "status")
            ),
            "latest_tracking_status": (
                _value(_get_attr(tracking, "status"))
                if tracking else None
            ),
            "latest_location": (
                _get_attr(tracking, "location")
                if tracking else None
            ),
            "latest_tracking_at": (
                _iso(_get_attr(tracking, "created_at"))
                if tracking else None
            ),
            "registered_at": _iso(
                _get_attr(baggage, "registered_at")
            ),
        })

    return rows


# ---------------------------------------------------------
# GROUND STAFF PERFORMANCE
# ---------------------------------------------------------

def _ground_staff_performance(
    db: Session,
    date_from=None,
    date_to=None,
):
    GroundStaff = _get_model("GroundStaff")
    GroundTask = _get_model("GroundTask")

    staff_items = db.query(GroundStaff).all()

    task_query = db.query(GroundTask)

    task_created = _get_column(
        GroundTask,
        "created_at",
    )

    task_query = _date_filter(
        task_query,
        task_created,
        date_from,
        date_to,
    )

    tasks = task_query.all()

    grouped = defaultdict(list)

    for task in tasks:
        staff_id = _get_attr(task, "ground_staff_id")

        if staff_id:
            grouped[str(staff_id)].append(task)

    rows = []

    for staff in staff_items:
        staff_id = str(staff.id)
        staff_tasks = grouped.get(staff_id, [])

        completed = 0
        pending = 0

        for task in staff_tasks:
            status = str(
                _value(_get_attr(task, "status", default=""))
            ).lower()

            if status == "completed":
                completed += 1

            if status in {
                "assigned",
                "in_progress",
                "blocked",
            }:
                pending += 1

        total = len(staff_tasks)

        rows.append({
            "ground_staff_id": staff_id,
            "employee_number": _get_attr(
                staff,
                "employee_number",
                "staff_number",
                "employee_id",
            ),
            "department": _value(
                _get_attr(staff, "department")
            ),
            "designation": _get_attr(
                staff,
                "designation",
                "job_title",
            ),
            "shift": _value(
                _get_attr(staff, "shift")
            ),
            "staff_status": _value(
                _get_attr(staff, "status")
            ),
            "total_tasks": total,
            "completed_tasks": completed,
            "pending_tasks": pending,
            "completion_rate": (
                round(completed / total * 100, 2)
                if total else 0.0
            ),
        })

    return rows


# ---------------------------------------------------------
# EQUIPMENT UTILIZATION
# ---------------------------------------------------------

def _equipment_utilization(
    db: Session,
    date_from=None,
    date_to=None,
):
    GroundEquipment = _get_model(
        "GroundEquipment",
        "Equipment",
    )

    GroundEquipmentUsage = _get_model(
        "GroundEquipmentUsage",
        "EquipmentUsage",
        "EquipmentTracking",
    )

    equipment_items = db.query(GroundEquipment).all()

    usage_query = db.query(GroundEquipmentUsage)

    started_column = _get_column(
        GroundEquipmentUsage,
        "started_at",
        "start_time",
        "created_at",
    )

    usage_query = _date_filter(
        usage_query,
        started_column,
        date_from,
        date_to,
    )

    usage_items = usage_query.all()

    grouped = defaultdict(list)

    for usage in usage_items:
        equipment_id = _get_attr(
            usage,
            "equipment_id",
            "ground_equipment_id",
        )

        if equipment_id:
            grouped[str(equipment_id)].append(usage)

    rows = []

    for equipment in equipment_items:
        equipment_id = str(equipment.id)
        usages = grouped.get(equipment_id, [])

        total_minutes = 0.0

        for usage in usages:
            started_at = _get_attr(
                usage,
                "started_at",
                "start_time",
            )

            ended_at = _get_attr(
                usage,
                "ended_at",
                "end_time",
            )

            if started_at and ended_at:
                duration = (
                    ended_at - started_at
                ).total_seconds() / 60

                total_minutes += max(0, duration)

        rows.append({
            "equipment_id": equipment_id,
            "equipment_code": _get_attr(
                equipment,
                "equipment_code",
                "equipment_number",
                "code",
            ),
            "equipment_name": _get_attr(
                equipment,
                "name",
                "equipment_name",
            ),
            "equipment_type": _value(
                _get_attr(
                    equipment,
                    "equipment_type",
                    "category",
                    "type",
                )
            ),
            "equipment_status": _value(
                _get_attr(equipment, "status")
            ),
            "usage_count": len(usages),
            "total_usage_minutes": round(
                total_minutes,
                2,
            ),
            "last_used_at": _iso(
                _get_attr(
                    equipment,
                    "last_used_at",
                    "updated_at",
                )
            ),
        })

    return rows


# ---------------------------------------------------------
# FLIGHT DELAY ANALYSIS
# ---------------------------------------------------------

def _flight_delay_analysis(
    db: Session,
    date_from=None,
    date_to=None,
):
    flights = _flight_rows(
        db,
        date_from,
        date_to,
        delayed_only=True,
    )

    rows = []

    for flight in flights:
        scheduled = _get_attr(
            flight,
            "scheduled_departure",
        )

        actual = _get_attr(
            flight,
            "actual_departure",
        )

        delay_minutes = None

        if scheduled and actual:
            delay_minutes = round(
                (actual - scheduled).total_seconds() / 60,
                2,
            )

        rows.append({
            "flight_id": str(flight.id),
            "flight_number": flight.flight_number,
            "airline": flight.airline,
            "scheduled_departure": _iso(scheduled),
            "actual_departure": _iso(actual),
            "delay_minutes": delay_minutes,
            "status": _value(
                _get_attr(flight, "status")
            ),
        })

    return rows


# ---------------------------------------------------------
# AIRCRAFT TURNAROUND REPORT
# ---------------------------------------------------------

def _aircraft_turnaround(
    db: Session,
    date_from=None,
    date_to=None,
):
    AircraftTurnaround = _get_model(
        "AircraftTurnaround"
    )

    query = db.query(AircraftTurnaround)

    scheduled_arrival = _get_column(
        AircraftTurnaround,
        "scheduled_arrival",
    )

    query = _date_filter(
        query,
        scheduled_arrival,
        date_from,
        date_to,
    )

    rows = []

    for item in query.all():
        actual_arrival = _get_attr(
            item,
            "actual_arrival",
        )

        actual_departure = _get_attr(
            item,
            "actual_departure",
        )

        duration_minutes = None

        if actual_arrival and actual_departure:
            duration_minutes = round(
                (
                    actual_departure - actual_arrival
                ).total_seconds() / 60,
                2,
            )

        rows.append({
            "turnaround_id": str(item.id),
            "turnaround_number": _get_attr(
                item,
                "turnaround_number",
            ),
            "flight_id": (
                str(item.flight_id)
                if _get_attr(item, "flight_id")
                else None
            ),
            "aircraft_registration": _get_attr(
                item,
                "aircraft_registration",
            ),
            "aircraft_type": _get_attr(
                item,
                "aircraft_type",
            ),
            "status": _value(
                _get_attr(item, "status")
            ),
            "scheduled_arrival": _iso(
                _get_attr(item, "scheduled_arrival")
            ),
            "scheduled_departure": _iso(
                _get_attr(item, "scheduled_departure")
            ),
            "actual_arrival": _iso(actual_arrival),
            "actual_departure": _iso(actual_departure),
            "turnaround_duration_minutes": duration_minutes,
        })

    return rows


# ---------------------------------------------------------
# MAIN REPORT SERVICE
# ---------------------------------------------------------

def get_report(
    db: Session,
    report_type: str,
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = 1,
    page_size: int = 20,
    sort_by: str = "flight_number",
    sort_order: str = "asc",
    paginate: bool = True,
):
    """
    Generate an airport operations report.

    Supported report types:
        daily-flight-operations
        monthly-flight-performance
        baggage-handling
        missing-baggage
        ground-staff-performance
        equipment-utilization
        flight-delay-analysis
        aircraft-turnaround

    Returns:
        (total_records, report_items)
    """

    if report_type not in REPORT_TYPES:
        raise ValueError(
            f"Unsupported report type: {report_type}"
        )

    _validate_dates(date_from, date_to)

    report_functions = {
        "daily-flight-operations": _daily_flight_operations,
        "monthly-flight-performance": _monthly_flight_performance,
        "baggage-handling": lambda db, date_from, date_to: (
            _baggage_rows(db, date_from, date_to)
        ),
        "missing-baggage": lambda db, date_from, date_to: (
            _baggage_rows(
                db,
                date_from,
                date_to,
                missing_only=True,
            )
        ),
        "ground-staff-performance": _ground_staff_performance,
        "equipment-utilization": _equipment_utilization,
        "flight-delay-analysis": _flight_delay_analysis,
        "aircraft-turnaround": _aircraft_turnaround,
    }

    items = report_functions[report_type](
        db,
        date_from,
        date_to,
    )

    if not paginate:
        return len(items), items

    total, paginated_items = _sort_and_paginate(
        items=items,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return total, paginated_items
