import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
import os

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HackronLogistics")

# Global Simulation State (Placeholder for now)
SIMULATION_RUNNING = False
SIMULATION_STARTED = False

from simulation import sim_instance

# Track the simulation task centrally
simulation_task: asyncio.Task = None

async def simulation_loop():
    """But simulation loop to tick the world."""
    global SIMULATION_RUNNING
    logger.info("Simulation loop started.")
    try:
        while SIMULATION_RUNNING:
            await sim_instance.tick()
            await asyncio.sleep(2)  # Tick every 2 seconds
    except Exception as e:
        logger.error(f"FATAL ERROR in simulation loop: {e}", exc_info=True)
    finally:
        logger.info("Simulation loop exited.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - don't start simulation automatically
    yield
    # Shutdown
    global SIMULATION_RUNNING
    SIMULATION_RUNNING = False
    logger.info("Simulation loop stopped.")

app = FastAPI(title="Adaptive Logistics Agent", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Frontend
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "../frontend")
if not os.path.exists(FRONTEND_DIR):
    os.makedirs(FRONTEND_DIR)

app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
async def read_home():
    return FileResponse(os.path.join(FRONTEND_DIR, "home.html"))

@app.get("/services")
async def read_services():
    return FileResponse(os.path.join(FRONTEND_DIR, "services.html"))

@app.get("/driver")
async def read_driver():
    return FileResponse(os.path.join(FRONTEND_DIR, "driver.html"))

@app.get("/manager")
async def read_manager():
    return FileResponse(os.path.join(FRONTEND_DIR, "operator.html"))

@app.get("/manager/fleet")
async def read_manager_fleet():
    return FileResponse(os.path.join(FRONTEND_DIR, "manager_fleet.html"))

@app.get("/manager/loads")
async def read_manager_loads():
    return FileResponse(os.path.join(FRONTEND_DIR, "manager_loads.html"))

@app.get("/manager/analytics")
async def read_manager_analytics():
    return FileResponse(os.path.join(FRONTEND_DIR, "manager_analytics.html"))

@app.get("/config")
async def read_config():
    return FileResponse(os.path.join(FRONTEND_DIR, "config.html"))

@app.get("/api/routes")
async def get_routes():
    """Return all routes in the system."""
    from map_data import ROUTES
    return [r.dict() for r in ROUTES.values()]

@app.post("/api/routes/{route_id}/toggle")
async def toggle_route(route_id: str):
    """Toggle route blocked status."""
    from map_data import ROUTES
    if route_id in ROUTES:
        ROUTES[route_id].is_active = not ROUTES[route_id].is_active
        status = "Open" if ROUTES[route_id].is_active else "Blocked"
        logger.info(f"Route {route_id} changed to {status}")
        return {"route_id": route_id, "is_active": ROUTES[route_id].is_active}
    return JSONResponse(status_code=404, content={"error": "Route not found"})

@app.get("/api/state")
async def get_state():
    """Return the current simulation state. Auto-starts if needed."""
    global SIMULATION_RUNNING, SIMULATION_STARTED, simulation_task
    
    is_task_active = simulation_task and not simulation_task.done()
    
    if not is_task_active:
        logger.info("Auto-starting/Restarting simulation loop.")
        SIMULATION_RUNNING = True
        SIMULATION_STARTED = True
        simulation_task = asyncio.create_task(simulation_loop())
    
    return sim_instance.get_state()

@app.get("/api/config")
async def get_config():
    """Return initial truck configuration."""
    return sim_instance.get_initial_config()

@app.put("/api/config")
async def set_config(data: dict):
    """Set initial truck configuration."""
    sim_instance.set_initial_config(data)
    return {"message": "Configuration updated successfully"}

@app.post("/api/start")
async def start_simulation():
    """Manually start/reset the simulation to initial state."""
    global SIMULATION_RUNNING, SIMULATION_STARTED, simulation_task
    
    # 1. Reset simulation backend state
    sim_instance._init_trucks()
    sim_instance.current_time = sim_instance.current_time.replace(hour=8, minute=0)
    
    # 2. Reset all routes to active (Open)
    from map_data import ROUTES
    for r in ROUTES.values():
        r.is_active = True
        
    logger.info("World state reset: Trucks returned to Hubs, all roads opened.")

    # 3. Ensure loop is running
    is_task_active = simulation_task and not simulation_task.done()
    if not is_task_active:
        SIMULATION_RUNNING = True
        SIMULATION_STARTED = True
        simulation_task = asyncio.create_task(simulation_loop())
        logger.info("Simulation loop (re)started via /api/start")
    
    return {"message": "Simulation started/reset"}

@app.post("/api/event")
async def manual_event(request: Request):
    """Manually trigger an event via POST."""
    try:
        data = await request.json()
        truck_id = data.get("truck_id")
        event_type = data.get("event_type", "ROADBLOCK")
        
        if not truck_id:
            return JSONResponse(status_code=400, content={"error": "truck_id required"})
            
        success = await sim_instance.trigger_event(truck_id, event_type)
        if success:
            logger.info(f"Manual {event_type} injected for {truck_id}")
            return {"status": "success", "truck_id": truck_id}
        else:
            return JSONResponse(status_code=404, content={"error": "Truck not found"})
    except Exception as e:
        logger.error(f"Event trigger failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.put("/api/trucks/{truck_id}")
async def update_truck(truck_id: str, data: dict):
    """Update truck fuel and capacity."""
    if truck_id not in sim_instance.trucks:
        return {"error": "Truck not found"}
    truck = sim_instance.trucks[truck_id]
    if "fuel_percent" in data:
        truck.fuel_percent = data["fuel_percent"]
    if "capacity_used_percent" in data:
        truck.capacity_used_percent = data["capacity_used_percent"]
    return {"message": "Truck updated successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
