from langchain.agents import create_tool_calling_agent, AgentExecutor
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
    from map_data import MAP_NODES
    all_points = [current_location] + destinations
    coords = []
    
    node_map = {n.node_id: (n.lat, n.lng) for n in MAP_NODES}
    
    for p in all_points:
        if p in node_map:
            coords.append(node_map[p])
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

# --- Agent Service ---

class AgentService:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            # Fallback for dev if env not set, though it should be
            print("Warning: GROQ_API_KEY not found.")
        
        self.llm = ChatGroq(
            temperature=0,
            model="llama3-70b-8192",
            api_key=api_key or "gsk_..." # Placeholder
        )
        
        self.tools = [get_route_info, check_traffic, optimize_route]
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an autonomous logistics agent managing a truck. "
                       "Your goal is to ensure timely delivery while minimizing cost and risk. "
                       "You have access to routing tools. "
                       "When an event occurs, analyze the situation, use tools to check alternatives if needed, and make a decision."),
            ("human", "Current State: {truck_state}\nEvent: {event}\nDetermine the best action."),
            ("placeholder", "{agent_scratchpad}"),
        ])
        
        self.agent = create_tool_calling_agent(self.llm, self.tools, prompt)
        self.agent_executor = AgentExecutor(agent=self.agent, tools=self.tools, verbose=True)

    async def decide(self, truck: TruckState, event_type: str, details: dict = {}) -> str:
        """
        Run the agent to make a decision.
        Returns a string describing the action (for now), or a structured object.
        """
        truck_dump = truck.json()
        
        response = await self.agent_executor.ainvoke({
            "truck_state": truck_dump,
            "event": f"{event_type}: {details}"
        })
        
        return response["output"]

# Global Instance
agent_service = AgentService()
