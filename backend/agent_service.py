# from langchain.agents import create_tool_calling_agent, AgentExecutor # Moved inside to avoid circular imports
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from typing import List, Optional
import os
from dotenv import load_dotenv

from models import TruckState, AgentDecision
from routing_engine import RoutingEngine

load_dotenv()

# --- Tools ---

@tool
async def get_route_info(start_lat: float, start_lng: float, end_lat: float, end_lng: float):
    """
    Calculates route distance and duration between two points using OSRM.
    DO NOT call this if start and end coordinates are the same.
    """
    if start_lat == end_lat and start_lng == end_lng:
        return {"distance_km": 0.0, "duration_min": 0.0, "message": "Start and end are identical."}
    return await RoutingEngine.get_route((start_lat, start_lng), (end_lat, end_lng))

@tool
def check_traffic(segment_id: str):
    """Checks traffic status for a specific road segment. Returns 'CLEAR', 'MODERATE', or 'HEAVY'."""
    # Mock traffic data
    import random
    return random.choice(["CLEAR", "CLEAR", "MODERATE", "HEAVY"])

@tool
async def optimize_route(current_location: str, destinations: List[str]):
    """
    Optimizes the order of visiting multiple destinations from a starting point.
    Returns the optimal sequence of locations.
    Useful when a truck has multiple remaining deliveries.
    """
    # 1. Get coordinates for all points (mock map lookup)
    from map_data import LOCATIONS_COORDS
    all_points = [current_location] + destinations
    coords = []
    
    for p in all_points:
        if p in LOCATIONS_COORDS:
            coords.append(LOCATIONS_COORDS[p])
        else:
            return f"Error: Location {p} unknown"
            
    # 2. Get Distance Matrix from OSRM
    matrix = await RoutingEngine.get_distance_matrix(coords)
    if not matrix:
        return "Error fetching distance matrix"
        
    # 3. Solve TSP with OR-Tools
    order_indices = RoutingEngine.solve_tsp(matrix)
    
    # 4. Convert back to IDs
    result_order = [all_points[i] for i in order_indices if i != 0] # Exclude start
    return result_order

@tool
def get_available_routes(origin: str, destination: str):
    """
    Returns a list of fixed pre-defined routes between a Hub (origin) and a Destination.
    Use this when a roadblock occurs to find alternative paths.
    """
    from map_data import ROUTES
    return [
        r.dict() for r in ROUTES.values() 
        if r.origin == origin and r.destination == destination and r.is_active
    ]

@tool
def get_fuel_stations():
    """Returns a list of all fuel stations and their coordinates in the system."""
    from map_data import LOCATIONS_COORDS
    return {k: v for k, v in LOCATIONS_COORDS.items() if k.startswith("FUEL")}

# --- Agent Service ---

class AgentService:
    def __init__(self):
        # ... (API key section)
        api_key = os.getenv("GROQ_API_KEY")
        
        self.llm = ChatGroq(
            temperature=0.1,
            model="llama-3.1-8b-instant",
            api_key=api_key or "gsk_..."
        )
        
        self.tools = [get_route_info, check_traffic, optimize_route, get_available_routes, get_fuel_stations]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an autonomous logistics agent managing a truck. "
                       "Your goal is to ensure timely delivery while minimizing cost and risk.\n\n"
                        "VALID LOCATION IDs:\n"
                       "- Hubs: HUB_SOUTH, HUB_EAST, HUB_NORTH_EAST\n"
                       "- Destinations: DEST_WEST, DEST_NORTH, DEST_NORTH_WEST\n"
                       "- Junctions: J_CENTRAL, J_BYPASS, J_NORTH\n"
                       "- Fuel Stations: FUEL_A, FUEL_B\n\n"
                       "When a roadblock or traffic jam occurs, you MUST follow these logical steps:\n"
                       "1.  **Analyze World State**: Identify the 'destination_node' and current active route.\n"
                       "2.  **Scan Options**: Use 'get_available_routes' to find ALL valid alternatives for the target destination.\n"
                       "3.  **Evaluate Risk**: Use 'check_traffic' on candidate segments to assess congestion.\n"
                       "4.  **Optimal Selection**: Select the route with the best balance of time, fuel, and risk.\n\n"
                       "**BEWARE**: Do NOT call tools redundantely. If you call 'get_available_routes', use its 'route_id' output directly. Do NOT call 'get_route_info' with the same start and end coordinates; it will fail.\n"
                       "If you are stuck, simply 'CONTINUE' with the current route if possible.\n\n"
                       "When a LOW_FUEL event occurs:\n"
                       "1.  **Find Stations**: Use 'get_fuel_stations' to find the closest one to your 'current_node'.\n"
                       "2.  **Plan Stop**: Select 'action': 'REROUTE' and provide 'new_route_nodes' that include the fuel station as an intermediate stop before the final destination.\n\n"
                       "IMPORTANT: Final response MUST be JSON exactly in this format:\n"
                       "{{\n"
                       "  \"action\": \"REROUTE | CONTINUE\",\n"
                       "  \"reasoning\": \"Summary of final decision.\",\n"
                       "  \"thoughts\": [\"Step 1: Found roadblock on R_EN_HWY\", \"Step 2: Scanned alternatives...\", ...],\n"
                       "  \"confidence\": 0.9,\n"
                       "  \"selected_route_id\": \"R_SW_HWY\",\n"
                       "  \"new_route_nodes\": [\"FUEL_A\", \"DEST_WEST\"]\n"
                       "}}"),
            ("human", "Current State: {truck_state}\nEvent: {event}\nDetermine best action."),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        # Import here to avoid circular imports and handle path variations
        try:
            from langchain.agents import create_tool_calling_agent, AgentExecutor
        except ImportError:
            try:
                # Fallback for some versions where top-level import might fail
                from langchain.agents.tool_calling_agent.base import create_tool_calling_agent
                from langchain.agents.agent import AgentExecutor
            except ImportError:
                # Fallback to langchain_classic if present (custom or specific version structure)
                from langchain_classic.agents.tool_calling_agent.base import create_tool_calling_agent
                from langchain_classic.agents.agent import AgentExecutor
            
        self.agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent, 
            tools=self.tools, 
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )
        self.cooldown_until = 0 # Unix timestamp to wait until after a 429 error

    def reset_cooldown(self):
        self.cooldown_until = 0
        print("[AI SERVICE] Rate-limit cooldown reset.")

    async def decide(self, truck: TruckState, event_type: str, details: dict = {}) -> AgentDecision:
        """
        Run the agent to make a decision.
        Returns an AgentDecision object.
        """
        # RATE LIMIT GUARD: If we recently hit a 429, skip LLM and go to heuristic
        import time
        if time.time() < self.cooldown_until:
            wait_sec = int(self.cooldown_until - time.time())
            return self._heuristic_fallback(truck, event_type, f"AI at capacity. Cooldown: {wait_sec}s.")

        # OPTIMIZATION: Do not send huge coordinate lists or long histories to the LLM.
        # This fixes the "413 Payload Too Large" error for low-tier TPM limits.
        truck_data = truck.dict()
        if "route_coordinates" in truck_data:
            del truck_data["route_coordinates"]
            
        # Limit history to last 5 entries to keep prompt small
        if "thoughts" in truck_data:
            truck_data["thoughts"] = truck_data["thoughts"][-5:]
        if "alerts" in truck_data:
            truck_data["alerts"] = truck_data["alerts"][-3:]
            
        import json
        truck_dump = json.dumps(truck_data)
        
        try:
            response = await self.agent_executor.ainvoke({
                "truck_state": truck_dump,
                "event": f"{event_type}: {details}"
            })
            
            output = response["output"]
            
            # Clean output if necessary (sometimes agents wrap JSON in markdown blocks)
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0].strip()
            elif "```" in output:
                output = output.split("```")[1].split("```")[0].strip()
            
            import json
            from datetime import datetime
            import uuid
            
            data = json.loads(output)
            
            # Extract data
            impact_data = {}
            if "selected_route_id" in data:
                impact_data["selected_route_id"] = data["selected_route_id"]
            if "new_route_nodes" in data:
                impact_data["new_route_nodes"] = data["new_route_nodes"]
            
            return AgentDecision(
                decision_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                truck_id=truck.truck_id,
                action=data.get("action", "CONTINUE"),
                reasoning=data.get("reasoning", "Agent completed analysis."),
                confidence=float(data.get("confidence", 1.0)),
                impact=impact_data
            ), data.get("thoughts", [])
            
        except Exception as e:
            return self._heuristic_fallback(truck, event_type, str(e))
            
    def _heuristic_fallback(self, truck: TruckState, event_type: str, error_msg: str) -> (AgentDecision, List[str]):
        """Provides a non-AI sensible action when the LLM is unavailable."""
        from datetime import datetime
        import uuid
        import time
        
        # If it's a rate limit error, set a cooldown of 2 minutes
        display_error = error_msg
        if "429" in str(error_msg):
            self.cooldown_until = time.time() + 120 # 2 minute silence
            display_error = "Groq API Rate Limit Reached (Daily Tokens). Switched to Heuristic Safety Protocol."
            print(f"[AI SERVICE] Rate limit reached. Muting AI for 120s. Using fallback.")

        action = "CONTINUE"
        impact_data = {}
        reasoning = display_error
        thoughts = ["System: LLM Unavailable. Initiating Safety Protocol."]

        if "LOW_FUEL" in event_type:
            from map_data import LOCATIONS_COORDS
            stations = {k: v for k, v in LOCATIONS_COORDS.items() if k.startswith("FUEL")}
            current_pos = (truck.location.lat, truck.location.lng)
            closest_station = min(stations.keys(), key=lambda s: ((stations[s][0]-current_pos[0])**2 + (stations[s][1]-current_pos[1])**2)**0.5)
            
            action = "REROUTE"
            impact_data = {"new_route_nodes": [closest_station, truck.destination_node]}
            reasoning = "SAFETY PROTOCOL: Low fuel detected and AI unavailable. Rerouting to nearest station."
            thoughts.append(f"Heuristic: Target {closest_station} as emergency stop.")

        elif "ROAD_CLOSED" in event_type or "BLOCKED" in event_type:
            from map_data import ROUTES
            alt_routes = [r for r in ROUTES.values() if r.is_active and r.route_id != truck.active_route_id and r.destination == truck.destination_node]
            if alt_routes:
                best_alt = alt_routes[0]
                action = "REROUTE"
                impact_data = {"selected_route_id": best_alt.route_id}
                reasoning = f"SAFETY PROTOCOL: Road blocked and AI unavailable. Switched to alternative: {best_alt.route_id}."
                thoughts.append(f"Heuristic: Using backup route {best_alt.route_id}.")

        return AgentDecision(
            decision_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            truck_id=truck.truck_id,
            action=action,
            reasoning=reasoning,
            confidence=0.0,
            impact=impact_data
        ), thoughts

# Global Instance
agent_service = AgentService()
