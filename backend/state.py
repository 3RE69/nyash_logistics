from models import TruckState, Location

TRUCKS = {
    "T1": TruckState(
        truck_id="T1",
        current_node="WH_1",
        route_nodes=["WH_1", "J2", "PUNE_C", "J1", "PCMC", "WH_3"],
        location=Location(lat=18.5793, lng=73.9786),
        fuel_percent=50,
        capacity_used_percent=70,
        status="EN_ROUTE",
        eta_minutes=90,
        alerts=[]
    ),
    "T2": TruckState(
        truck_id="T2",
        current_node="WH_5",
        route_nodes=["WH_5", "J3", "HINJ", "J1", "PUNE_C", "WH_2"],
        location=Location(lat=18.7286, lng=73.6752),
        fuel_percent=80,
        capacity_used_percent=30,
        status="EN_ROUTE",
        eta_minutes=110,
        alerts=[]
    ),
    "T3": TruckState(
        truck_id="T3",
        current_node="PCMC",
        route_nodes=["PCMC", "J1", "PUNE_C", "J2", "WH_4"],
        location=Location(lat=18.6298, lng=73.7997),
        fuel_percent=18,
        capacity_used_percent=90,
        status="EN_ROUTE",
        eta_minutes=70,
        alerts=[]
    )
}

DECISIONS = {tid: [] for tid in TRUCKS}
