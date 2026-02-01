import requests
import polyline
import time
from typing import List, Tuple, Dict, Any
from map_data import ROUTES, Route

OSRM_BASE_URL = "http://router.project-osrm.org"

# Simple In-Memory Cache
_ROUTE_CACHE = {}
_LAST_OSRM_CALL = 0
_OSRM_CIRCUIT_OPEN = False
_OSRM_CIRCUIT_RESET_TIME = 0

import threading
_OSRM_LOCK = threading.Lock()

import asyncio

async def _osrm_cooldown():
    """Ensures at least 2.5 seconds between ANY OSRM request without blocking the event loop."""
    global _LAST_OSRM_CALL, _OSRM_CIRCUIT_OPEN, _OSRM_CIRCUIT_RESET_TIME
    
    # Check Circuit Breaker
    if _OSRM_CIRCUIT_OPEN:
        if time.time() < _OSRM_CIRCUIT_RESET_TIME:
            raise Exception("OSRM Circuit Open: Rate limit exceeded recently. Using fallback.")
        else:
            _OSRM_CIRCUIT_OPEN = False
            print("[OSRM] Circuit Closed. Retrying service...")

    # Enforce Cooldown
    elapsed = time.time() - _LAST_OSRM_CALL
    if elapsed < 2.5:
        await asyncio.sleep(2.5 - elapsed)
    _LAST_OSRM_CALL = time.time()

def _open_osrm_circuit():
    """Opens the circuit breaker for 5 minutes after a 429 error."""
    global _OSRM_CIRCUIT_OPEN, _OSRM_CIRCUIT_RESET_TIME
    with _OSRM_LOCK:
        print("[OSRM] 429 Detected. Opening Circuit Breaker for 5 minutes.")
        _OSRM_CIRCUIT_OPEN = True
        _OSRM_CIRCUIT_RESET_TIME = time.time() + 300 # 5 minutes

class RoutingEngine:
    # -------------------------------------------------
    # REAL ROUTING (Geometry + Distance)
    # -------------------------------------------------
    @staticmethod
    async def get_route(start: Tuple[float, float], end: Tuple[float, float]) -> Dict[str, Any]:
        """
        Get real route from OSRM between two points (lat, lng).
        Includes caching and error fallbacks.
        """
        # 1. Check for identical points
        if abs(start[0] - end[0]) < 0.0001 and abs(start[1] - end[1]) < 0.0001:
            return {
                "distance_km": 0.0,
                "duration_min": 0.0,
                "geometry": "",
                "coordinates": [start]
            }

        # 2. Check Cache
        cache_key = f"{start[0]:.5f},{start[1]:.5f}|{end[0]:.5f},{end[1]:.5f}"
        if cache_key in _ROUTE_CACHE:
            return _ROUTE_CACHE[cache_key]

        start_str = f"{start[1]},{start[0]}"
        end_str = f"{end[1]},{end[0]}"
        url = f"{OSRM_BASE_URL}/route/v1/driving/{start_str};{end_str}?overview=full&geometries=polyline"

        # 3. Request with Retry Logic
        for attempt in range(2):
            try:
                await _osrm_cooldown()
                response = requests.get(url, timeout=5) # Reduced timeout for faster fallback
                if response.status_code == 429:
                    _open_osrm_circuit()
                response.raise_for_status()
                data = response.json()

                if data["code"] == "Ok":
                    route = data["routes"][0]
                    result = {
                        "distance_km": route["distance"] / 1000.0,
                        "duration_min": route["duration"] / 60.0,
                        "geometry": route["geometry"],
                        "coordinates": polyline.decode(route["geometry"])
                    }
                    _ROUTE_CACHE[cache_key] = result
                    return result
            except Exception:
                # Silent failure to avoid log spam, fallback handles it
                pass

        # 4. Fallback: Straight-Line (Great Circle approximation)
        print("Using Straight-Line Fallback for routing.")
        # Rough distance: 1 deg ~ 111 km
        dist_lat = (end[0] - start[0]) * 111
        dist_lng = (end[1] - start[1]) * 111 * 0.9 # Adjusted for latitude
        direct_dist = (dist_lat**2 + dist_lng**2)**0.5
        
        return {
            "distance_km": direct_dist,
            "duration_min": direct_dist / 0.8, # Assume 48km/h avg
            "geometry": "",
            "coordinates": [start, end]
        }

    @staticmethod
    async def get_distance_matrix(locations: List[Tuple[float, float]]) -> List[List[float]]:
        # ... (caching logic)
        cache_key = tuple(sorted(locations))
        if not '_TABLE_CACHE' in globals():
            globals()['_TABLE_CACHE'] = {}
            
        if cache_key in globals()['_TABLE_CACHE']:
            return globals()['_TABLE_CACHE'][cache_key]

        coords = ";".join([f"{loc[1]},{loc[0]}" for loc in locations])
        url = f"{OSRM_BASE_URL}/table/v1/driving/{coords}"

        try:
            await _osrm_cooldown()
            response = requests.get(url, timeout=10)
            if response.status_code == 429:
                _open_osrm_circuit()
            response.raise_for_status()
            data = response.json()
            globals()['_TABLE_CACHE'][cache_key] = data["durations"]
            return data["durations"]
        except Exception as e:
            print(f"Table Exception: {e}")
            # Fallback: simple Euclidean distance matrix (scaled by avg speed)
            size = len(locations)
            matrix = [[0.0] * size for _ in range(size)]
            for i in range(size):
                for j in range(size):
                    if i == j: continue
                    l1, l2 = locations[i], locations[j]
                    dist = ((l1[0]-l2[0])**2 + (l1[1]-l2[1])**2)**0.5 * 111000 # meters
                    matrix[i][j] = dist / 13.0 # ~47 km/h in m/s
            return matrix

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
