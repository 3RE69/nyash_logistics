from datetime import datetime, timedelta
import random
import uuid
import asyncio
from typing import Dict, List
from models import TruckState, Location, AgentDecision
from routing_engine import RoutingEngine
# Will import AgentService later to avoid circular imports if possible, or inject it.

class Simulation:
    def __init__(self):
        self.trucks: Dict[str, TruckState] = {}
        self.current_time = datetime.now().replace(hour=8, minute=0, second=0)
        self.events = []
        
        # Initialize some dummy trucks
        self._init_trucks()

    def _init_trucks(self):
        # Start some trucks around Pune
        t1 = TruckState(
            truck_id="T1",
            current_node="PUNE_C", 
            route_nodes=["PUNE_C", "J1", "HINJ"], # Logical route
            location=Location(lat=18.5204, lng=73.8567), # Pune
            fuel_percent=100,
            capacity_used_percent=50,
            status="EN_ROUTE",
            eta_minutes=0,
            alerts=[]
        )
        self.trucks["T1"] = t1

    async def tick(self):
        """Advance time by 15 minutes (virtual time) every tick."""
        self.current_time += timedelta(minutes=15)
        # print(f"Sim Time: {self.current_time.strftime('%H:%M')}")

        for truck_id, truck in self.trucks.items():
            if truck.status == "EN_ROUTE":
                await self._move_truck(truck)
                
            # Random event generation (10% chance)
            if random.random() < 0.1:
                await self._trigger_random_event(truck)

    async def _move_truck(self, truck: TruckState):
        """
        Move truck along its route. 
        Simple interpolation for prototype.
        """
        if not truck.route_nodes or len(truck.route_nodes) < 2:
            truck.status = "IDLE"
            return
            
        # Target is the next node in the route
        next_node_id = truck.route_nodes[1]
        # In a real app we'd look up coordinates of next_node_id from MAP_NODES
        # For this demo, let's assume we have a helper or look it up from map_data
        from map_data import MAP_NODES
        target_node = next((n for n in MAP_NODES if n.node_id == next_node_id), None)
        
        if not target_node:
            print(f"Error: Node {next_node_id} not found")
            return

        # Simple linear interpolation (approx 10km per tick)
        # Lat/Lng approx: 0.01 degrees ~= 1.1km
        speed_factor = 0.05 
        
        dx = target_node.lat - truck.location.lat
        dy = target_node.lng - truck.location.lng
        
        dist = (dx**2 + dy**2)**0.5
        
        if dist < speed_factor:
            # Arrived at node
            truck.location.lat = target_node.lat
            truck.location.lng = target_node.lng
            truck.current_node = next_node_id
            truck.route_nodes.pop(0) # Remove visited node
            # print(f"{truck.truck_id} reached {next_node_id}")
        else:
            # Move towards node
            ratio = speed_factor / dist
            truck.location.lat += dx * ratio
            truck.location.lng += dy * ratio

    async def _trigger_random_event(self, truck: TruckState):
        from agent_service import agent_service
        event_type = random.choice(["TRAFFIC_JAM", "VEHICLE_BREAKDOWN", "NEW_LOAD_OFFER"])
        print(f"Event {event_type} for {truck.truck_id}")
        
        # Call Agent
        try:
            decision = await agent_service.decide(truck, event_type)
            print(f"Agent Decision for {truck.truck_id}: {decision}")
        except Exception as e:
            print(f"Agent failed: {e}")

    def get_state(self):
        return {
            "time": self.current_time.strftime("%H:%M"),
            "trucks": [t.dict() for t in self.trucks.values()]
        }

# Global Instance
sim_instance = Simulation()
