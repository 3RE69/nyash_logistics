import requests
import polyline
from typing import List, Tuple, Dict, Any
from map_data import ROUTES, Route

OSRM_BASE_URL = "http://router.project-osrm.org"


class RoutingEngine:
    # -------------------------------------------------
    # REAL ROUTING (Geometry + Distance)
    # -------------------------------------------------
    @staticmethod
    def get_route(start: Tuple[float, float], end: Tuple[float, float]) -> Dict[str, Any]:
        """
        Get real route from OSRM between two points (lat, lng).
        """
        start_str = f"{start[1]},{start[0]}"
        end_str = f"{end[1]},{end[0]}"
        url = f"{OSRM_BASE_URL}/route/v1/driving/{start_str};{end_str}?overview=full&geometries=polyline"

        try:
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()

            if data["code"] != "Ok":
                return None

            route = data["routes"][0]
            return {
                "distance_km": route["distance"] / 1000.0,
                "duration_min": route["duration"] / 60.0,
                "geometry": route["geometry"],
                "coordinates": polyline.decode(route["geometry"])
            }
        except Exception as e:
            print(f"Routing Exception: {e}")
            return None

    @staticmethod
    def get_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[float]]:
        coords = ";".join([f"{loc[1]},{loc[0]}" for loc in locations])
        url = f"{OSRM_BASE_URL}/table/v1/driving/{coords}"

        try:
            response = requests.get(url, timeout=15)
            data = response.json()
            return data["durations"]
        except Exception as e:
            print(f"Table Exception: {e}")
            return []

    @staticmethod
    def solve_tsp(distance_matrix: List[List[float]]) -> List[int]:
        try:
            from ortools.constraint_solver import routing_enums_pb2
            from ortools.constraint_solver import pywrapcp
        except ImportError:
            print("OR-Tools not found. Falling back to simple sequence.")
            return list(range(len(distance_matrix)))

        if not distance_matrix or len(distance_matrix) <= 1:
            return list(range(len(distance_matrix)))

        manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            return distance_matrix[
                manager.IndexToNode(from_index)
            ][
                manager.IndexToNode(to_index)
            ]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )

        solution = routing.SolveWithParameters(search_parameters)
        if not solution:
            return []

        index = routing.Start(0)
        route = []
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        return route

    # -------------------------------------------------
    # AGENTIC CONSTRAINT LAYER (NEW, SMALL, CRITICAL)
    # -------------------------------------------------
    @staticmethod
    def get_allowed_routes(origin: str, destination: str) -> List[Route]:
        """
        Returns only routes that exist in the simulation world
        and are currently active.
        """
        return [
            r for r in ROUTES.values()
            if r.origin == origin
            and r.destination == destination
            and r.is_active
        ]

    @staticmethod
    def deactivate_route(route_id: str):
        if route_id in ROUTES:
            ROUTES[route_id].is_active = False

    @staticmethod
    def activate_route(route_id: str):
        if route_id in ROUTES:
            ROUTES[route_id].is_active = True
