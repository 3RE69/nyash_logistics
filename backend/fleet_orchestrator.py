import uvicorn
import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict
import os
import logging
from dotenv import load_dotenv

# LangChain Imports
from langchain_groq import ChatGroq
from langchain.agents import create_openai_tools_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool

from routing_engine import RoutingEngine

load_dotenv()

# Logger setup
logger = logging.getLogger("FleetOrchestrator")

# --- 1. CONFIGURATION ---
# API Key from environment
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    logger.warning("GROQ_API_KEY not found in environment variables.")

app = FastAPI(title="Fleet Orchestrator Agent")

# --- 2. THE TOOLS (OpenStreetMap Integration) ---

@tool
def get_osm_route_stats(start_coords: str, end_coords: str):
    """
    Calculates distance and duration between two points using OpenStreetMap (OSRM).
    Input format: "longitude,latitude"
    """
    try:
        start_lon, start_lat = map(float, start_coords.split(','))
        end_lon, end_lat = map(float, end_coords.split(','))

        routing_engine = RoutingEngine()
        route = routing_engine.get_route(
            (start_lat, start_lon),
            (end_lat, end_lon)
        )

        if not route:
            return {"error": "No route found"}

        return {
            "source": "OpenStreetMap",
            "distance_km": round(route["distance_km"], 2),
            "duration_min": round(route["duration_min"], 1)
        }
    except Exception as e:
        return {"error": f"Routing Failed: {str(e)}"}

# --- 3. THE AGENT BRAIN (LangChain) ---

def build_agent():
    # A. Setup the Model
    llm = ChatGroq(
        temperature=0,
        model="llama-3.1-70b-versatile",
        api_key=GROQ_API_KEY
    )
    
    # B. Tools
    tools = [get_osm_route_stats]
    
    # C. Define the Prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", """
        You are an AI Fleet Orchestrator. 
        Your goal is to assign the best Truck to the Order.
        
        RULES:
        1. ALWAYS check the distance using the `get_osm_route_stats` tool before deciding.
        2. If a truck has low fuel (<20%), do not assign it to long trips (>50km).
        3. Prioritize the truck that can arrive fastest.
        
        Return the decision as a clean string explaining WHY.
        """),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    
    # D. Create Agent
    agent = create_openai_tools_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
    
    return agent_executor

# Initialize Agent
agent_executor = build_agent()

# --- 4. FASTAPI DATA MODELS ---

class Truck(BaseModel):
    id: str
    coords: str  # "lon,lat"
    fuel: int    # %

class Order(BaseModel):
    id: str
    coords: str  # "lon,lat"
    value: int

class FleetRequest(BaseModel):
    trucks: List[Truck]
    order: Order

# --- 5. THE API ENDPOINT ---

@app.post("/orchestrate")
async def orchestrate_fleet(request: FleetRequest):
    """
    Endpoint that receives Truck + Order data and asks the AI to decide.
    """
    
    # 1. Construct a natural language query for the agent
    context_str = f"I have a new Order {request.order.id} at location {request.order.coords}.\n"
    context_str += "Here is my fleet status:\n"
    
    for truck in request.trucks:
        context_str += f"- Truck {truck.id}: Location {truck.coords}, Fuel {truck.fuel}%.\n"
    
    context_str += "Which truck should take this order and why? Use the map tool to calculate real driving distances."

    # 2. Invoke the Agent
    logger.info(f"🤖 AI Thinking about: {context_str}")
    
    try:
        response = await agent_executor.ainvoke({"input": context_str})
        decision = response["output"]
        logger.info(f"🤖 Decision: {decision}")
        return {"decision": decision}
    except Exception as e:
        logger.error(f"Agent execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Agent execution failed")

# --- 6. RUN SERVER ---
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)