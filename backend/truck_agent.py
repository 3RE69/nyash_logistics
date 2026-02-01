from groq import Groq
from models import AgentDecision, TruckState
from datetime import datetime
import uuid, json

client = Groq()

SYSTEM_PROMPT = """
You are an autonomous truck logistics agent operating on a road network.
You must make safe, realistic decisions when disruptions occur.
Return ONLY valid JSON:
{
  "action": "CONTINUE | REROUTE | STOP_FOR_FUEL | WAIT | ACCEPT_LOAD | REJECT_LOAD",
  "reasoning": "string",
  "confidence": number between 0 and 1,
  "impact": {}
}
"""

def llm_decide(truck: TruckState, event_type: str, payload: dict):
    decision_id = str(uuid.uuid4())

    prompt = f"""
Truck ID: {truck.truck_id}
Current Node: {truck.current_node}
Route: {truck.route_nodes}
Fuel: {truck.fuel_percent}%
Capacity Used: {truck.capacity_used_percent}%
Status: {truck.status}
ETA: {truck.eta_minutes}

Event: {event_type}
Details: {payload}
"""

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )

        data = json.loads(resp.choices[0].message.content)

        return AgentDecision(
            decision_id=decision_id,
            timestamp=datetime.utcnow(),
            truck_id=truck.truck_id,
            action=data["action"],
            reasoning=data["reasoning"],
            confidence=float(data["confidence"]),
            impact=data.get("impact", {})
        )

    except Exception as e:
        fallback = "REROUTE" if event_type in ["TRAFFIC", "ROADBLOCK"] else "STOP_FOR_FUEL"

        return AgentDecision(
            decision_id=decision_id,
            timestamp=datetime.utcnow(),
            truck_id=truck.truck_id,
            action=fallback,
            reasoning=f"Fallback due to LLM error: {e}",
            confidence=0.5,
            impact={}
        )
