
from pydantic import BaseModel


class FlightDashboard(BaseModel):
    total_flights: int
    scheduled_flights: int
    delayed_flights: int
    cancelled_flights: int
    arrived_flights: int
    departed_flights: int


class BaggageDashboard(BaseModel):
    baggage_processed: int
    delayed_baggage: int
    missing_baggage: int


class GroundOperationsDashboard(BaseModel):
    active_checkin_counters: int
    available_gates: int
    pending_ground_tasks: int
    average_turnaround_duration_minutes: float | None
    total_operational_incidents: int
    active_operational_incidents: int


class DashboardOverview(BaseModel):
    flights: FlightDashboard
    baggage: BaggageDashboard
    ground_operations: GroundOperationsDashboard
