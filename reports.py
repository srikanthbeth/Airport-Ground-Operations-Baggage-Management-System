
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ReportType(str, Enum):
    DAILY_FLIGHT_OPERATIONS = "daily-flight-operations"
    MONTHLY_FLIGHT_PERFORMANCE = "monthly-flight-performance"
    BAGGAGE_HANDLING = "baggage-handling"
    MISSING_BAGGAGE = "missing-baggage"
    GROUND_STAFF_PERFORMANCE = "ground-staff-performance"
    EQUIPMENT_UTILIZATION = "equipment-utilization"
    FLIGHT_DELAY_ANALYSIS = "flight-delay-analysis"
    AIRCRAFT_TURNAROUND = "aircraft-turnaround"


class ReportResponse(BaseModel):
    report_type: str
    total: int
    page: int
    page_size: int
    items: list[dict[str, Any]] = Field(default_factory=list)
