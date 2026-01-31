import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# Logger setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HackronLogistics")

# Global Simulation State (Placeholder for now)
SIMULATION_RUNNING = False

from simulation import sim_instance

async def simulation_loop():
    """But simulation loop to tick the world."""
    logger.info("Simulation loop started.")
    while SIMULATION_RUNNING:
        await sim_instance.tick()
        await asyncio.sleep(2)  # Tick every 2 seconds

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global SIMULATION_RUNNING
    SIMULATION_RUNNING = True
    asyncio.create_task(simulation_loop())
    yield
    # Shutdown
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

@app.get("/manager/alerts")
async def read_manager_alerts():
    return FileResponse(os.path.join(FRONTEND_DIR, "manager_alerts.html"))

@app.get("/api/state")
async def get_state():
    """Return the current simulation state (trucks, routes, etc)."""
    return sim_instance.get_state()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
