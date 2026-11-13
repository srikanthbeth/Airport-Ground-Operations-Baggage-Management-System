
from fastapi import FastAPI

from core.config import settings
from routes import auth, users
from routes.airports import router as airports_router
from routes.terminals import router as terminals_router
from routes.flights import router as flights_router
from routes.gates import router as gates_router
from routes.counters import router as counters_router
from routes.resource_assignments import router as resource_assignments_router
from routes.passengers import router as passengers_router
from routes import checkins, boarding_passes
from routes import baggage
from routes import baggage_tracking
from routes import baggage_screenings
from routes.ground_staff import router as ground_staff_router
from routes.ground_tasks import router as ground_tasks_router
from routes.aircraft_turnarounds import router as aircraft_turnarounds_router
from routes.ground_equipment import router as ground_equipment_router
from routes.operational_incidents import router as operational_incidents_router
from routes.flight_delays import router as flight_delays_router
from routes.resource_allocations import router as resource_allocations_router
from routes.dashboard import router as dashboard_router
from routes.reports import router as reports_router
from routes.audit_logs import router as audit_logs_router



app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Airport Ground Operations "
        "and Baggage Management System"
    ),
    version="1.0.0"
)


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(airports_router)
app.include_router(terminals_router)
app.include_router(flights_router)
app.include_router(gates_router)
app.include_router(counters_router)
app.include_router(resource_assignments_router)
app.include_router(passengers_router)
app.include_router(checkins.router)
app.include_router(boarding_passes.router)
app.include_router(baggage.router)
app.include_router(baggage_tracking.router)
app.include_router(baggage_screenings.router)
app.include_router(ground_staff_router)
app.include_router(ground_tasks_router)
app.include_router(aircraft_turnarounds_router)
app.include_router(ground_equipment_router)
app.include_router(operational_incidents_router)
app.include_router(flight_delays_router)
app.include_router(resource_allocations_router)
app.include_router(dashboard_router)
app.include_router(reports_router)
app.include_router(audit_logs_router)



@app.get("/", tags=["Health"])
def root():

    return {
        "message": "Airport Ground Operations API is running",
        "status": "success"
    }


@app.get("/health", tags=["Health"])
def health_check():

    return {
        "status": "healthy",
        "database": "PostgreSQL",
        "application": settings.APP_NAME
    }
