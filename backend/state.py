from models import TruckState, Location

TRUCKS = {
    "T1": TruckState(
        truck_id="T1",
        current_node="HUB_SOUTH",
        route_nodes=["HUB_SOUTH", "J_BYPASS", "DEST_WEST"],
        location=Location(lat=18.4466, lng=73.8567),
        fuel_percent=50,
        capacity_used_percent=70,
        status="EN_ROUTE",
        eta_minutes=30,
        alerts=[]
    ),
    "T2": TruckState(
        truck_id="T2",
        current_node="HUB_EAST",
        route_nodes=["HUB_EAST", "J_CENTRAL", "J_NORTH", "DEST_NORTH"],
        location=Location(lat=18.5089, lng=73.9260),
        fuel_percent=80,
        capacity_used_percent=30,
        status="EN_ROUTE",
        eta_minutes=70,
        alerts=[]
    ),
    "T3": TruckState(
        truck_id="T3",
        current_node="HUB_NORTH_EAST",
        route_nodes=["HUB_NORTH_EAST", "J_NORTH", "DEST_NORTH_WEST"],
        location=Location(lat=18.5793, lng=73.9787),
        fuel_percent=18,
        capacity_used_percent=90,
        status="EN_ROUTE",
        eta_minutes=60,
        alerts=[]
    )
}

DECISIONS = {tid: [] for tid in TRUCKS}
