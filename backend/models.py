from pydantic import BaseModel
from typing import List, Literal
from datetime import datetime


class Location(BaseModel):
    lat: float
    lng: float


class Route(BaseModel):
    route_id: str
    origin: str
    destination: str
    distance_km: float
    base_time_min: int
    fuel_cost: float
    toll_cost: float
    congestion_risk: float
    is_active: bool = True


class MapNode(BaseModel):
    node_id: str
    lat: float
    lng: float
    type: Literal["CITY", "WAREHOUSE", "FUEL_STATION", "JUNCTION"]


class MapEdge(BaseModel):
    from_node: str
    to_node: str
    status: Literal["OPEN", "TRAFFIC", "BLOCKED"]


class TruckState(BaseModel):
    truck_id: str
    current_node: str
    destination_node: str = "" # Final target
    route_nodes: List[str]
    location: Location
    fuel_percent: int
    capacity_used_percent: int
    status: Literal["EN_ROUTE", "REROUTING", "STOPPED_FOR_FUEL", "IDLE", "ARRIVED"]
    eta_minutes: int
    alerts: List[str] = []
    route_coordinates: List[Location] = []
    active_route_id: str = ""


class AgentDecision(BaseModel):
    decision_id: str
    timestamp: datetime
    truck_id: str
    action: Literal[
        "CONTINUE",
        "REROUTE",
        "STOP_FOR_FUEL",
        "WAIT",
        "ACCEPT_LOAD",
        "REJECT_LOAD"
    ]
    reasoning: str
    confidence: float
    impact: dict = {}
