from models import MapNode, MapEdge

MAP_NODES = [
    MapNode("PUNE_C", 18.5204, 73.8567, "CITY"),
    MapNode("HINJ", 18.5913, 73.7389, "CITY"),
    MapNode("PCMC", 18.6298, 73.7997, "CITY"),

    MapNode("WH_1", 18.5793, 73.9786, "WAREHOUSE"),
    MapNode("WH_2", 18.4464, 73.8640, "WAREHOUSE"),
    MapNode("WH_3", 18.6519, 73.7645, "WAREHOUSE"),
    MapNode("WH_4", 18.5089, 73.9259, "WAREHOUSE"),
    MapNode("WH_5", 18.7286, 73.6752, "WAREHOUSE"),

    MapNode("FUEL_1", 18.5642, 73.7769, "FUEL_STATION"),
    MapNode("FUEL_2", 18.4881, 73.8570, "FUEL_STATION"),
    MapNode("FUEL_3", 18.6735, 73.8080, "FUEL_STATION"),

    MapNode("J1", 18.5586, 73.7890, "JUNCTION"),
    MapNode("J2", 18.4865, 73.9056, "JUNCTION"),
    MapNode("J3", 18.6366, 73.8015, "JUNCTION"),
]

MAP_EDGES = [
    MapEdge("PUNE_C", "J1", "OPEN"),
    MapEdge("J1", "HINJ", "OPEN"),
    MapEdge("J1", "PCMC", "OPEN"),
    MapEdge("PCMC", "WH_3", "OPEN"),

    MapEdge("PUNE_C", "J2", "OPEN"),
    MapEdge("J2", "WH_1", "OPEN"),
    MapEdge("J2", "WH_4", "OPEN"),

    MapEdge("HINJ", "J3", "OPEN"),
    MapEdge("J3", "WH_5", "OPEN"),

    MapEdge("J1", "FUEL_1", "OPEN"),
    MapEdge("J2", "FUEL_2", "OPEN"),
    MapEdge("PCMC", "FUEL_3", "OPEN"),
]
