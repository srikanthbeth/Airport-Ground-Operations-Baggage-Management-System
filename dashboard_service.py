
from sqlalchemy import func, distinct, extract
from sqlalchemy.orm import Session

from core.constants import (
    FlightStatus,
    CounterStatus,
    GateStatus,
    BaggageTrackingStatus,
    GroundTaskStatus,
    AircraftTurnaroundStatus,
    IncidentStatus,
)

from models.flight import Flight
from models.checkin_counter import CheckInCounter
from models.gate import Gate
from models.baggage import Baggage
from models.baggage_tracking import BaggageTracking
from models.ground_task import GroundTask
from models.aircraft_turnaround import AircraftTurnaround
from models.operational_incident import OperationalIncident


def get_dashboard_overview(db: Session):

    # -------------------------------------------------
    # FLIGHT DASHBOARD
    # -------------------------------------------------

    total_flights = db.query(Flight).count()

    scheduled_flights = db.query(Flight).filter(
        Flight.status == FlightStatus.SCHEDULED
    ).count()

    delayed_flights = db.query(Flight).filter(
        Flight.status == FlightStatus.DELAYED
    ).count()

    cancelled_flights = db.query(Flight).filter(
        Flight.status == FlightStatus.CANCELLED
    ).count()

    arrived_flights = db.query(Flight).filter(
        Flight.status == FlightStatus.ARRIVED
    ).count()

    departed_flights = db.query(Flight).filter(
        Flight.status == FlightStatus.DEPARTED
    ).count()

    # -------------------------------------------------
    # CHECK-IN COUNTERS AND GATES
    # -------------------------------------------------

    active_checkin_counters = db.query(CheckInCounter).filter(
        CheckInCounter.status == CounterStatus.ACTIVE
    ).count()

    available_gates = db.query(Gate).filter(
        Gate.status == GateStatus.ACTIVE
    ).count()

    # -------------------------------------------------
    # BAGGAGE DASHBOARD
    # -------------------------------------------------

    processed_statuses = [
        BaggageTrackingStatus.SORTED,
        BaggageTrackingStatus.LOADED,
        BaggageTrackingStatus.IN_TRANSIT,
        BaggageTrackingStatus.UNLOADED,
        BaggageTrackingStatus.ARRIVED,
        BaggageTrackingStatus.CLAIMED,
    ]

    baggage_processed = (
        db.query(
            func.count(distinct(BaggageTracking.baggage_id))
        )
        .filter(BaggageTracking.status.in_(processed_statuses))
        .scalar()
        or 0
    )

    missing_baggage = (
        db.query(
            func.count(distinct(BaggageTracking.baggage_id))
        )
        .filter(
            BaggageTracking.status == BaggageTrackingStatus.LOST
        )
        .scalar()
        or 0
    )

    delayed_baggage = (
        db.query(func.count(distinct(Baggage.id)))
        .join(Flight, Baggage.flight_id == Flight.id)
        .filter(Flight.status == FlightStatus.DELAYED)
        .scalar()
        or 0
    )

    # -------------------------------------------------
    # GROUND TASKS
    # -------------------------------------------------

    pending_ground_tasks = db.query(GroundTask).filter(
        GroundTask.status.in_([
            GroundTaskStatus.ASSIGNED,
            GroundTaskStatus.BLOCKED,
        ])
    ).count()

    # -------------------------------------------------
    # AIRCRAFT TURNAROUND DURATION
    # -------------------------------------------------

    turnaround_duration = (
        db.query(
            func.avg(
                extract(
                    "epoch",
                    AircraftTurnaround.actual_departure
                    - AircraftTurnaround.actual_arrival,
                ) / 60.0
            )
        )
        .filter(
            AircraftTurnaround.status == AircraftTurnaroundStatus.COMPLETED,
            AircraftTurnaround.actual_arrival.isnot(None),
            AircraftTurnaround.actual_departure.isnot(None),
        )
        .scalar()
    )

    average_turnaround_duration_minutes = (
        round(float(turnaround_duration), 2)
        if turnaround_duration is not None
        else None
    )

    # -------------------------------------------------
    # OPERATIONAL INCIDENTS
    # -------------------------------------------------

    total_operational_incidents = db.query(
        OperationalIncident
    ).count()

    active_operational_incidents = db.query(
        OperationalIncident
    ).filter(
        OperationalIncident.status.in_([
            IncidentStatus.OPEN,
            IncidentStatus.ACKNOWLEDGED,
            IncidentStatus.IN_PROGRESS,
        ])
    ).count()

    # -------------------------------------------------
    # RESPONSE
    # -------------------------------------------------

    return {
        "flights": {
            "total_flights": total_flights,
            "scheduled_flights": scheduled_flights,
            "delayed_flights": delayed_flights,
            "cancelled_flights": cancelled_flights,
            "arrived_flights": arrived_flights,
            "departed_flights": departed_flights,
        },
        "baggage": {
            "baggage_processed": baggage_processed,
            "delayed_baggage": delayed_baggage,
            "missing_baggage": missing_baggage,
        },
        "ground_operations": {
            "active_checkin_counters": active_checkin_counters,
            "available_gates": available_gates,
            "pending_ground_tasks": pending_ground_tasks,
            "average_turnaround_duration_minutes":
                average_turnaround_duration_minutes,
            "total_operational_incidents":
                total_operational_incidents,
            "active_operational_incidents":
                active_operational_incidents,
        },
    }
