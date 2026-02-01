# Adaptive Logistics Agent

**Continuous, agent-driven optimization for road freight operations**

Traditional road logistics is planned as isolated trips. Once a truck starts moving, routing, pricing, and load decisions rarely adapt — leading to idle time, empty return journeys, and lost income for drivers.

**Adaptive Logistics Agent** reframes logistics as a **continuous decision-making problem**, where autonomous AI agents observe, reason, and act while vehicles are already in motion.

---

## Core Idea

Each truck operates as an **AI agent** that:
- Continuously observes its state (location, fuel, capacity, ETA)
- Reacts to real-world events (traffic, fuel risk, new loads)
- Reasons about tradeoffs (time vs profit vs utilization)
- Produces **explainable, confidence-scored decisions**

Agents run independently but share a **global world model**, enabling fleet-level coordination.

---

## Key Features

- Agentic decision loop (observe → reason → act)
- Real-time adaptation during a trip
- Multi-truck, fleet-aware design
- Explainable AI decisions using an LLM
- Interactive web-based frontend visualization
- Modular and extensible architecture

---

## System Architecture

```
┌────────────┐      ┌──────────────┐
│ Road Map   │◄────►│ World Model  │
└────────────┘      └──────────────┘
                           │
                    ┌──────▼──────┐
                    │ Truck Agent │
                    │  (LLM)      │
                    └──────┬──────┘
                           │
                   ┌───────▼────────┐
                   │ Agent Decision │
                   │ (Action + Why) │
                   └───────┬────────┘
                           │
                 ┌─────────▼─────────┐
                 │ Frontend Dashboard │
                 └───────────────────┘
```

---

## Project Structure

```
adaptive-logistics-agent/
│
├── models.py
├── map_data.py
├── state.py
├── truck_agent.py
├── api.py
│
├── frontend/
│   └── logistics-ui/
│       ├── src/App.jsx
│       └── src/App.css
│
└── README.md
```

---

## Tech Stack

### Backend
- Python
- FastAPI
- Pydantic
- Groq LLM (LLaMA-3)

### Frontend
- React (Vite)
- SVG-based map rendering
- REST API polling

---

## How To Run

### Backend

```bash
pip install fastapi uvicorn pydantic groq
export GROQ_API_KEY=your_api_key_here
uvicorn api:app --reload
```

### Frontend

```bash
cd frontend/logistics-ui
npm install
npm run dev
```

---

## 🏁 Summary

Adaptive Logistics Agent demonstrates how AI agents can transform road freight from static planning into a continuous, adaptive system.

