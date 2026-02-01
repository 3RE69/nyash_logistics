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
        self.initial_config = {
            "T1": {"fuel_percent": 100, "capacity_used_percent": 80},
            "T2": {"fuel_percent": 90, "capacity_used_percent": 60},
            "T3": {"fuel_percent": 85, "capacity_used_percent": 70}
        }
        
        # Initialize trucks
        self._init_trucks()

    def get_initial_config(self):
        """Return the initial configuration for trucks."""
        return self.initial_config

    def set_initial_config(self, config: dict):
        """Set the initial configuration for trucks."""
        self.initial_config.update(config)
        # Reinitialize trucks with new config
        self._init_trucks()

    def _init_trucks(self):
        from map_data import LOCATIONS_COORDS
        
        # Truck 1: SOUTH Hub -> WEST Dest (High-Speed Bypass first)
        t1_path = ["HUB_SOUTH", "J_BYPASS", "DEST_WEST"]
        c1 = LOCATIONS_COORDS["HUB_SOUTH"]
        
        self.trucks["T1"] = TruckState(
            truck_id="T1",
            current_node="HUB_SOUTH", 
            destination_node="DEST_WEST",
            route_nodes=t1_path,
            location=Location(lat=c1[0], lng=c1[1]),
            fuel_percent=self.initial_config["T1"]["fuel_percent"],
            capacity_used_percent=self.initial_config["T1"]["capacity_used_percent"],
            status="EN_ROUTE",
            eta_minutes=30,
            route_coordinates=self._resolve_route(t1_path),
            active_route_id="R_SW_HWY"
        )

        # Truck 2: EAST Hub -> NORTH Dest (Main route via Central)
        t2_path = ["HUB_EAST", "J_CENTRAL", "J_NORTH", "DEST_NORTH"]
        c2 = LOCATIONS_COORDS["HUB_EAST"]

        self.trucks["T2"] = TruckState(
            truck_id="T2",
            current_node="HUB_EAST",
            destination_node="DEST_NORTH",
            route_nodes=t2_path,
            location=Location(lat=c2[0], lng=c2[1]),
            fuel_percent=self.initial_config["T2"]["fuel_percent"],
            capacity_used_percent=self.initial_config["T2"]["capacity_used_percent"],
            status="EN_ROUTE",
            eta_minutes=70,
            route_coordinates=self._resolve_route(t2_path),
            active_route_id="R_EN_HWY"
        )

        # Truck 3: NE Hub -> NW Dest (Direct route)
        t3_path = ["HUB_NORTH_EAST", "J_NORTH", "DEST_NORTH_WEST"]
        c3 = LOCATIONS_COORDS["HUB_NORTH_EAST"]
        
        self.trucks["T3"] = TruckState(
            truck_id="T3",
            current_node="HUB_NORTH_EAST",
            destination_node="DEST_NORTH_WEST",
            route_nodes=t3_path,
            location=Location(lat=c3[0], lng=c3[1]),
            fuel_percent=self.initial_config["T3"]["fuel_percent"],
            capacity_used_percent=self.initial_config["T3"]["capacity_used_percent"],
            status="EN_ROUTE",
            eta_minutes=60,
            route_coordinates=self._resolve_route(t3_path),
            active_route_id="R_NENW_DIRECT"
        )

    def _resolve_route(self, route_nodes: List[str]) -> List[Location]:
        from map_data import LOCATIONS_COORDS
        coords = []
        for nid in route_nodes:
            if nid in LOCATIONS_COORDS:
                c = LOCATIONS_COORDS[nid]
                coords.append(Location(lat=c[0], lng=c[1]))
        return coords

    async def tick(self):
        """Advance time by 1 minute (virtual time) every tick."""
        self.current_time += timedelta(minutes=1) 
        
        from map_data import ROUTES
        for truck_id, truck in self.trucks.items():
            if truck.status == "EN_ROUTE" or truck.status == "REROUTING":
                # Proactive Check: Is the current route blocked manually?
                if truck.active_route_id in ROUTES and not ROUTES[truck.active_route_id].is_active:
                    # Avoid spamming AI if we already alerted/started rerouting for this block
                    if not any("Blocked route detected" in a for a in truck.alerts):
                        print(f"[SIM] Blocked route detected for {truck.truck_id}! Triggering AI...")
                        truck.alerts = ["Blocked route detected! Requesting AI reroute..."]
                        await self._trigger_random_event(truck, "ROAD_CLOSED_BY_DISPATCH")
                    continue # Skip movement while blocked
                
                await self._move_truck(truck)
                
            # Random event generation (REDUCED to 0.5% chance per tick to save AI tokens)
            if random.random() < 0.005: 
                await self._trigger_random_event(truck)

    async def _move_truck(self, truck: TruckState):
        if truck.status == "REFUELING":
            if truck.wait_time_ticks > 0:
                truck.wait_time_ticks -= 1
                print(f"[SIM] {truck.truck_id} Refueling... {truck.wait_time_ticks} ticks left")
                return
            else:
                truck.fuel_percent = 100
                truck.status = "EN_ROUTE"
                truck.alerts = ["Refueling complete. Tank size: 100%"]
                print(f"[SIM] {truck.truck_id} Refueling complete!")
                # Don't return, allow movement in same tick if next node exists
        
        if not truck.route_nodes or len(truck.route_nodes) < 2:
            truck.status = "IDLE"
            return

        # Simple coordinate progression
        # We move 0.008 degrees per tick (~0.9km)
        speed = 0.015 
        
        target_coord = truck.route_coordinates[1] if len(truck.route_coordinates) > 1 else None
        if not target_coord:
            truck.status = "IDLE"
            return

        curr_lat, curr_lng = truck.location.lat, truck.location.lng
        t_lat, t_lng = target_coord.lat, target_coord.lng

        dist = ((t_lat - curr_lat)**2 + (t_lng - curr_lng)**2)**0.5
        
        if dist < speed:
            # Reached next coordinate point
            truck.location = Location(lat=t_lat, lng=t_lng)
            if len(truck.route_coordinates) > 1:
                truck.route_coordinates.pop(0)
            
            # If we reached a node, update current_node
            if truck.route_nodes and len(truck.route_nodes) > 1:
                truck.current_node = truck.route_nodes[1]
                truck.route_nodes.pop(0)
            
            # Arrival Check: No more nodes to visit
            if not truck.route_nodes or len(truck.route_nodes) <= 1:
                truck.status = "ARRIVED"
                truck.eta_minutes = 0
                print(f"[SIM] {truck.truck_id} has ARRIVED at {truck.current_node}")
            
            # Refuel Check: If we reached a fuel station
            if "FUEL" in truck.current_node:
                truck.status = "REFUELING"
                truck.wait_time_ticks = 5 # Wait for 5 ticks to refuel
                truck.alerts = ["Refueling in progress..."]
                print(f"[SIM] {truck.truck_id} started REFUELING at {truck.current_node}")

        else:
            # Interpolate
            ratio = speed / dist
            new_lat = curr_lat + (t_lat - curr_lat) * ratio
            new_lng = curr_lng + (t_lng - curr_lng) * ratio
            truck.location = Location(lat=new_lat, lng=new_lng)
        
        # Fuel Consumption
        # Consumption depends on speed and capacity used
        consumption = 0.5 * (1 + truck.capacity_used_percent / 100.0)
        truck.fuel_percent = max(0, truck.fuel_percent - consumption)
        
        if truck.fuel_percent < 20 and truck.status not in ["REROUTING", "REFUELING", "STOPPED_FOR_FUEL"]:
            # Check if we already have an active fuel stop alert to avoid spam
            if not any("Heading to fuel station" in a for a in truck.alerts):
                print(f"[SIM] Low Fuel detected for {truck.truck_id} ({truck.fuel_percent:.1f}%)! Triggering AI...")
                await self._trigger_random_event(truck, "LOW_FUEL")

        if truck.eta_minutes > 0:
            truck.eta_minutes -= 1

        # More detailed print
        print(f"[SIM] {truck.truck_id} status: {truck.status}, fuel: {truck.fuel_percent:.1f}%, pos: ({truck.location.lat:.4f}, {truck.location.lng:.4f})")

    async def trigger_event(self, truck_id: str, event_type: str = None):
        """Manually trigger an event for a specific truck."""
        if truck_id in self.trucks:
            await self._trigger_random_event(self.trucks[truck_id], event_type)
            return True
        return False

    async def _trigger_random_event(self, truck: TruckState, event_type: str = None):
        from agent_service import agent_service
        if not event_type:
            event_type = random.choice(["TRAFFIC_JAM", "NEW_LOAD_OFFER"])
        
        try:
            decision, thoughts = await agent_service.decide(truck, event_type)
            truck.thoughts = thoughts # Capture logical steps
            
            if decision and decision.action == "REROUTE":
               print(f"[DISPATCH] {truck.truck_id} Rerouting. Reasoning: {decision.reasoning}")
               
               from map_data import ROUTE_PATHS, ROUTES
               new_route_id = decision.impact.get("selected_route_id")
               new_nodes = decision.impact.get("new_route_nodes")
               
               if new_nodes:
                   # Agent provided direct node sequence (e.g., to include a fuel stop)
                   truck.route_nodes = [truck.current_node] + new_nodes
                   truck.status = "REROUTING"
                   truck.active_route_id = "CUSTOM_AI_ROUTE"
                   # Approximate ETA: 10 mins per node
                   truck.eta_minutes = len(new_nodes) * 10
               elif new_route_id and new_route_id in ROUTE_PATHS:
                   new_nodes = ROUTE_PATHS[new_route_id]
                   # Start new route from current position
                   truck.route_nodes = [truck.current_node] + new_nodes
                   truck.status = "REROUTING"
                   truck.active_route_id = new_route_id
                   
                   # Update ETA based on route data
                   if new_route_id in ROUTES:
                       truck.eta_minutes = ROUTES[new_route_id].base_time_min
               
               # Re-calculate coordinates
               truck.route_coordinates = self._resolve_route(truck.route_nodes)
               
               # Log the decision to state so frontend can see
               truck.alerts = [f"Rerouted: {decision.reasoning}"]
               
               if event_type == "LOW_FUEL":
                   truck.status = "REROUTING" # Let it move to the fuel station
                   truck.alerts = ["Heading to fuel station..."]
                         
            elif decision and decision.action == "CONTINUE":
                print(f"[DISPATCH] {truck.truck_id} holding course. Reasoning: {decision.reasoning}")
                
            # SAFETY OVERRIDE: If the AI returns CONTINUE but fuel is critically low, force a reroute
            if event_type == "LOW_FUEL" and (not decision or decision.action != "REROUTE"):
                print(f"[DISPATCH] {truck.truck_id} low fuel safety override triggered.")
                from agent_service import agent_service
                decision, thoughts = agent_service._heuristic_fallback(truck, "LOW_FUEL", "Safety override: Fuel critical.")
                # Recursively apply this heuristic decision
                new_nodes = decision.impact.get("new_route_nodes")
                if new_nodes:
                    truck.route_nodes = [truck.current_node] + new_nodes
                    truck.status = "REROUTING"
                    truck.active_route_id = "CUSTOM_AI_ROUTE"
                    truck.route_coordinates = self._resolve_route(truck.route_nodes)
                    truck.alerts = ["Heading to fuel station (Safety Override)"]
                    truck.thoughts.append("Simulation: Overrode AI decision to ensure vehicle safety.")

        except Exception as e:
            print(f"[ERROR] Dispatch logic failed: {e}")

    def get_state(self):
        return {
            "time": self.current_time.strftime("%H:%M"),
            "trucks": [t.dict() for t in self.trucks.values()]
        }

# Global Instance
sim_instance = Simulation()
