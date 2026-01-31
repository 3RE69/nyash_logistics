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
def get_route_info(start_lat: float, start_lng: float, end_lat: float, end_lng: float):
    """Calculates route distance and duration between two points using OSRM."""
    return RoutingEngine.get_route((start_lat, start_lng), (end_lat, end_lng))

@tool
def check_traffic(segment_id: str):
    """Checks traffic status for a specific road segment. Returns 'CLEAR', 'MODERATE', or 'HEAVY'."""
    # Mock traffic data
    import random
    return random.choice(["CLEAR", "CLEAR", "MODERATE", "HEAVY"])

@tool
def optimize_route(current_location: str, destinations: List[str]):
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
    matrix = RoutingEngine.get_distance_matrix(coords)
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
        
        self.tools = [get_route_info, check_traffic, optimize_route, get_available_routes]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an autonomous logistics agent managing a truck. "
                       "Your goal is to ensure timely delivery while minimizing cost and risk.\n\n"
                       "VALID LOCATION IDs:\n"
                       "- Hubs: HUB_SOUTH, HUB_EAST, HUB_NORTH_EAST\n"
                       "- Destinations: DEST_WEST, DEST_NORTH, DEST_NORTH_WEST\n"
                       "- Junctions: J_CENTRAL, J_BYPASS, J_NORTH\n\n"
                       "When a roadblock or traffic jam occurs, you MUST:\n"
                       "1. Identify the 'destination_node' from the 'truck_state'.\n"
                       "2. Use 'get_available_routes' to find options between origin Hub and that specific destination_node.\n"
                       "3. Only use IDs from the list above. Do NOT hallucinate names like 'FINAL_DEST'.\n"
                       "4. Decide whether to REROUTE to a specific valid selected_route_id or CONTINUE.\n\n"
                       "IMPORTANT: Final response MUST be JSON exactly in this format:\n"
                       "{{\n"
                       "  \"action\": \"REROUTE | CONTINUE\",\n"
                       "  \"reasoning\": \"State which route ID was chosen and why.\",\n"
                       "  \"confidence\": 0.9,\n"
                       "  \"selected_route_id\": \"R_SW_HWY\"\n"
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
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    async def decide(self, truck: TruckState, event_type: str, details: dict = {}) -> AgentDecision:
        """
        Run the agent to make a decision.
        Returns an AgentDecision object.
        """
        # OPTIMIZATION: Do not send huge coordinate lists to the LLM.
        # This fixes the "413 Payload Too Large" error.
        truck_data = truck.dict()
        if "route_coordinates" in truck_data:
            del truck_data["route_coordinates"]
            
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
            )
            
        except Exception as e:
            print(f"Agent Processing Error: {e}")
            from datetime import datetime
            import uuid
            return AgentDecision(
                decision_id=str(uuid.uuid4()),
                timestamp=datetime.utcnow(),
                truck_id=truck.truck_id,
                action="CONTINUE",
                reasoning=f"Fallback due to processing error: {e}",
                confidence=0.0,
                impact={}
            ) 

# Global Instance
agent_service = AgentService()
