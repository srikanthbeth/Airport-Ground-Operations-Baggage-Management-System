
from enum import Enum


class UserRole(str, Enum):
    SUPER_ADMIN = "super_admin"
    AIRPORT_OPERATIONS_MANAGER = "airport_operations_manager"
    FLIGHT_OPERATIONS_OFFICER = "flight_operations_officer"
    GROUND_STAFF_SUPERVISOR = "ground_staff_supervisor"
    BAGGAGE_HANDLING_STAFF = "baggage_handling_staff"
    CHECK_IN_AGENT = "check_in_agent"
    GATE_AGENT = "gate_agent"
    MAINTENANCE_STAFF = "maintenance_staff"


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"


class AirportStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TerminalStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_MAINTENANCE = "under_maintenance"

class FlightStatus(str, Enum):
    SCHEDULED = "scheduled"
    CHECK_IN_OPEN = "check_in_open"
    BOARDING = "boarding"
    DEPARTED = "departed"
    DELAYED = "delayed"
    ARRIVED = "arrived"
    CANCELLED = "cancelled"


class FlightType(str, Enum):
    DOMESTIC = "domestic"
    INTERNATIONAL = "international"

class GateStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_MAINTENANCE = "under_maintenance"


class CounterStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNDER_MAINTENANCE = "under_maintenance"


class ResourceAssignmentStatus(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"


class PassengerStatus(str, Enum):
    ACTIVE = "active"
    CANCELLED = "cancelled"


class IdentificationType(str, Enum):
    PASSPORT = "passport"
    NATIONAL_ID = "national_id"
    OTHER = "other"

class CheckInStatus(str, Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class BoardingPassStatus(str, Enum):
    ACTIVE = "active"
    VOID = "void"


class BaggageType(str, Enum):
    CHECKED = "checked"
    CABIN = "cabin"
    SPECIAL = "special"


class BaggageStatus(str, Enum):
    REGISTERED = "registered"
    CANCELLED = "cancelled"

class BaggageTrackingStatus(str, Enum):
    RECEIVED = "received"
    SORTED = "sorted"
    LOADED = "loaded"
    IN_TRANSIT = "in_transit"
    UNLOADED = "unloaded"
    ARRIVED = "arrived"
    CLAIMED = "claimed"
    LOST = "lost"
    DAMAGED = "damaged"


class BaggageScreeningStatus(str, Enum):
    IN_PROGRESS = "in_progress"
    CLEARED = "cleared"
    REJECTED = "rejected"
    MANUAL_INSPECTION = "manual_inspection"


class ScreeningMethod(str, Enum):
    X_RAY = "x_ray"
    CT_SCAN = "ct_scan"
    ETD = "etd"
    PHYSICAL = "physical"



class GroundStaffDepartment(str, Enum):
    BAGGAGE_HANDLING = "baggage_handling"
    CHECK_IN = "check_in"
    GATE_OPERATIONS = "gate_operations"
    RAMP_OPERATIONS = "ramp_operations"
    MAINTENANCE = "maintenance"
    SECURITY = "security"
    CLEANING = "cleaning"
    CUSTOMER_SERVICE = "customer_service"


class GroundStaffShift(str, Enum):
    MORNING = "morning"
    EVENING = "evening"
    NIGHT = "night"
    ROTATIONAL = "rotational"


class GroundStaffStatus(str, Enum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"



class GroundTaskCategory(str, Enum):
    BAGGAGE_HANDLING = "baggage_handling"
    AIRCRAFT_CLEANING = "aircraft_cleaning"
    CABIN_PREPARATION = "cabin_preparation"
    EQUIPMENT_TRANSPORT = "equipment_transport"
    RAMP_SUPPORT = "ramp_support"
    PASSENGER_ASSISTANCE = "passenger_assistance"
    SECURITY_CHECK = "security_check"
    MAINTENANCE = "maintenance"
    OTHER = "other"


class GroundTaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class GroundTaskStatus(str, Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AircraftTurnaroundStatus(str, Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    DELAYED = "delayed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TurnaroundMilestone(str, Enum):
    PASSENGERS_DISEMBARKED = "passengers_disembarked"
    BAGGAGE_UNLOADED = "baggage_unloaded"
    CLEANING_COMPLETED = "cleaning_completed"
    CATERING_COMPLETED = "catering_completed"
    REFUELLING_COMPLETED = "refuelling_completed"
    BAGGAGE_LOADED = "baggage_loaded"
    BOARDING_COMPLETED = "boarding_completed"
    CHOCKS_OFF = "chocks_off"

from enum import Enum


class GroundEquipmentType(str, Enum):
    BAGGAGE_CART = "baggage_cart"
    GROUND_POWER_UNIT = "ground_power_unit"
    AIRCRAFT_TUG = "aircraft_tug"
    PASSENGER_STAIRS = "passenger_stairs"
    LOADING_EQUIPMENT = "loading_equipment"


class GroundEquipmentStatus(str, Enum):
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    OUT_OF_SERVICE = "out_of_service"

class IncidentCategory(str, Enum):
    SAFETY = "safety"
    SECURITY = "security"
    BAGGAGE = "baggage"
    AIRCRAFT = "aircraft"
    EQUIPMENT = "equipment"
    PASSENGER = "passenger"
    STAFFING = "staffing"
    FACILITY = "facility"
    OTHER = "other"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"

from enum import Enum


class FlightDelayReason(str, Enum):
    WEATHER = "weather"
    TECHNICAL = "technical"
    AIRCRAFT_MAINTENANCE = "aircraft_maintenance"
    CREW_AVAILABILITY = "crew_availability"
    AIR_TRAFFIC_CONTROL = "air_traffic_control"
    SECURITY = "security"
    BAGGAGE_HANDLING = "baggage_handling"
    GROUND_OPERATIONS = "ground_operations"
    PASSENGER_RELATED = "passenger_related"
    OTHER = "other"


class FlightDelayStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    RESOLVED = "resolved"


class FlightDelayImpact(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AllocationResourceType(str, Enum):
    GATE = "gate"
    COUNTER = "counter"
    GROUND_STAFF = "ground_staff"
    GROUND_EQUIPMENT = "ground_equipment"


class ResourceAllocationStatus(str, Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
