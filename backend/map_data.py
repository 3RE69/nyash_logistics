from typing import Dict, List
from models import Route, MapNode

# --- NODES IN OUR CLOSED WORLD (With coordinates for simulation) ---
LOCATIONS_COORDS = {
    # Hubs (Starts)
    "HUB_SOUTH": (18.4466, 73.8567),   # Katraj
    "HUB_EAST": (18.5089, 73.9260),    # Hadapsar
    "HUB_NORTH_EAST": (18.5793, 73.9787), # Wagholi
    
    # Dest (Ends)
    "DEST_WEST": (18.5913, 73.7389),   # Hinjewadi
    "DEST_NORTH": (18.7606, 73.8635),  # Chakan
    "DEST_NORTH_WEST": (18.7217, 73.6756), # Talegaon
    
    # Mid-points (Junctions)
    "J_CENTRAL": (18.5204, 73.8567),
    "J_BYPASS": (18.5074, 73.8077),
    "J_NORTH": (18.6298, 73.7997),
}

# Legacy Compatibility Layer for Visualization
MAP_NODES = [
    MapNode(node_id=name, lat=coords[0], lng=coords[1], type="CITY")
    for name, coords in LOCATIONS_COORDS.items()
]

# --- DIVERGENT ROUTES (Multiple paths for same Start/End) ---
ROUTES: Dict[str, Route] = {
    # Trip A: SOUTH -> WEST
    "R_SW_HWY": Route(
        route_id="R_SW_HWY", origin="HUB_SOUTH", destination="DEST_WEST", 
        distance_km=15, base_time_min=30, fuel_cost=6.0, toll_cost=100, congestion_risk=0.4
    ),
    "R_SW_CITY": Route(
        route_id="R_SW_CITY", origin="HUB_SOUTH", destination="DEST_WEST", 
        distance_km=22, base_time_min=55, fuel_cost=8.5, toll_cost=0, congestion_risk=0.8
    ),
    "R_SW_SATELLITE": Route(
        route_id="R_SW_SATELLITE", origin="HUB_SOUTH", destination="DEST_WEST", 
        distance_km=28, base_time_min=45, fuel_cost=9.0, toll_cost=50, congestion_risk=0.2
    ),

    # Trip B: EAST -> NORTH
    "R_EN_HWY": Route(
        route_id="R_EN_HWY", origin="HUB_EAST", destination="DEST_NORTH", 
        distance_km=40, base_time_min=70, fuel_cost=11.0, toll_cost=120, congestion_risk=0.5
    ),
    "R_EN_BYPASS": Route(
        route_id="R_EN_BYPASS", origin="HUB_EAST", destination="DEST_NORTH", 
        distance_km=45, base_time_min=85, fuel_cost=13.0, toll_cost=0, congestion_risk=0.3
    ),
    "R_EN_VILLAGE": Route(
        route_id="R_EN_VILLAGE", origin="HUB_EAST", destination="DEST_NORTH", 
        distance_km=38, base_time_min=110, fuel_cost=10.0, toll_cost=0, congestion_risk=0.1
    ),

    # Trip C: NE -> NW
    "R_NENW_DIRECT": Route(
        route_id="R_NENW_DIRECT", origin="HUB_NORTH_EAST", destination="DEST_NORTH_WEST", 
        distance_km=35, base_time_min=60, fuel_cost=10.0, toll_cost=80, congestion_risk=0.5
    ),
    "R_NENW_ALT": Route(
        route_id="R_NENW_ALT", origin="HUB_NORTH_EAST", destination="DEST_NORTH_WEST", 
        distance_km=42, base_time_min=90, fuel_cost=12.0, toll_cost=0, congestion_risk=0.7
    ),
}

# --- ROUTE PATHS (The nodes that make up each fixed route ID) ---
# This tells the simulation WHICH nodes to follow for a specific Route ID
ROUTE_PATHS = {
    "R_SW_HWY": ["J_BYPASS", "DEST_WEST"],
    "R_SW_CITY": ["J_CENTRAL", "DEST_WEST"],
    "R_SW_SATELLITE": ["J_CENTRAL", "J_NORTH", "DEST_WEST"],
    "R_EN_HWY": ["J_CENTRAL", "J_NORTH", "DEST_NORTH"],
    "R_EN_BYPASS": ["J_BYPASS", "J_CENTRAL", "DEST_NORTH"],
    "R_EN_VILLAGE": ["HUB_NORTH_EAST", "DEST_NORTH"],
    "R_NENW_DIRECT": ["J_NORTH", "DEST_NORTH_WEST"],
    "R_NENW_ALT": ["J_CENTRAL", "DEST_NORTH_WEST"],
}


def get_routes_between(origin: str, destination: str) -> List[Route]:
    return [
        r for r in ROUTES.values()
        if r.origin == origin and r.destination == destination and r.is_active
    ]
