import requests
import polyline
from typing import List, Tuple, Dict, Any

OSRM_BASE_URL = "http://router.project-osrm.org"

class RoutingEngine:
    @staticmethod
    def get_route(start: Tuple[float, float], end: Tuple[float, float]) -> Dict[str, Any]:
        """
        Get route from OSRM between two points (lat, lng).
        OSRM expects (lng, lat).
        """
        # Coordinates for OSRM are {lon},{lat}
        start_str = f"{start[1]},{start[0]}"
        end_str = f"{end[1]},{end[0]}"
        
        url = f"{OSRM_BASE_URL}/route/v1/driving/{start_str};{end_str}?overview=full&geometries=polyline"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            if data["code"] != "Ok":
                print(f"OSRM Error: {data['code']}")
                return None
                
            route = data["routes"][0]
            return {
                "distance_km": route["distance"] / 1000.0,
                "duration_min": route["duration"] / 60.0,
                "geometry": route["geometry"],
                "coordinates": polyline.decode(route["geometry"]) # Returns [(lat, lng)...]
            }
        except Exception as e:
            print(f"Routing Exception: {e}")
            return None

    @staticmethod
    def get_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[float]]:
        """
        Get duration matrix for list of locations.
        """
        # Build coordinate string
        coords = ";".join([f"{loc[1]},{loc[0]}" for loc in locations])
        url = f"{OSRM_BASE_URL}/table/v1/driving/{coords}"
        
        try:
            response = requests.get(url, timeout=5)
            data = response.json()
            # Returns durations in seconds
            return data["durations"]
        except Exception as e:
            print(f"Table Exception: {e}")
            return []
    @staticmethod
    def solve_tsp(distance_matrix: List[List[float]]) -> List[int]:
        """
        Solves Traveling Salesperson Problem using Google OR-Tools.
        Returns the ordered list of indices.
        """
        from ortools.constraint_solver import routing_enums_pb2
        from ortools.constraint_solver import pywrapcp
        
        manager = pywrapcp.RoutingIndexManager(len(distance_matrix), 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )

        solution = routing.SolveWithParameters(search_parameters)
        
        if solution:
            index = routing.Start(0)
            route = []
            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            return route
        return []

