# AI Travel Agent

A multi-agent travel planning assistant built with the **OpenAI Agents SDK**, with an optional **voice interface** powered by **LiveKit**. The system orchestrates specialized sub-agents to plan itineraries, estimate costs, and provide local tips, then returns a single structured travel plan.

## How It Works

The system is built around a central **Travel Agent** that acts as an orchestrator. Instead of doing everything itself, it delegates tasks to three specialized agents (used as tools):

| Agent | Responsibility | Output |
|---|---|---|
| **Planner Agent** | Builds day-by-day itineraries and sequences activities | `destination`, `duration`, `summary` |
| **Budget Agent** | Estimates lodging, food, transport, and activity costs | `cost` |
| **Local Guide Agent** | Suggests restaurants, culture, and local highlights | `tips` |

All three sub-agents use `WebSearchTool()` to pull current, real-world information rather than relying on the model's static knowledge.

### Guardrail

Before the Travel Agent processes a request, a **Budget Guardrail Agent** checks whether the requested budget is realistic for the destination and duration. If the budget is clearly too low, the guardrail trips and the request is rejected with an explanation (`InputGuardrailTripwireTriggered`), instead of producing a misleading plan.

### Flow

```
User request
   │
   ▼
Budget Guardrail Agent  ──► unrealistic? → stop, explain why
   │ realistic
   ▼
Travel Agent (orchestrator)
   ├─► Planner Agent  (itinerary)
   ├─► Budget Agent   (cost)
   └─► Local Guide Agent (tips)
   │
   ▼
Structured TravelOutput (JSON)
```

The final response always conforms to the `TravelOutput` schema:
```json
{
  "destination": "string",
  "duration": "string",
  "summary": "string",
  "cost": "string",
  "tips": "string"
}
```

## Project Structure

```
.
├── main.py            # Core agent logic: CLI entry point, agents, guardrail
├── voice.py           # Voice interface using LiveKit, wraps travel_agent as a tool
└── requirements.txt    # Python dependencies
```

## Requirements

- Python 3.10+
- An OpenAI API key
- (Optional, for voice) A LiveKit account/server and its credentials

Install dependencies:
```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with at least:
```
OPENAI_API_KEY=your_api_key_here
```
(Add any LiveKit-related environment variables if you plan to run `voice.py`.)

## Usage

### Text/CLI mode

Run the main script and answer the prompt:
```bash
python main.py
```
You'll be asked to describe your trip (e.g. *"Plan a 5-day trip to Istanbul under $800"*), and the agent will print a structured travel plan to the console. Conversation state is persisted locally via `SQLiteSession` (`travel_agent.sqlits`).

### Voice mode

Run the LiveKit voice worker:
```bash
python voice.py
```
This starts a voice assistant ("Dan") that:
1. Greets the caller and asks where they'd like to go
2. Calls the same `travel_agent` pipeline (planner → budget → local guide) via a `plan_trip` tool when the user requests a plan
3. Summarizes the structured result back to the user conversationally, using speech

## Notes / Known Issues

- `requirements.txt` lists `python-dotenv` twice — safe to remove the duplicate.
- The SQLite session filename uses the extension `.sqlits` (likely a typo for `.sqlite3` or `.db`) — this still works, but may be worth renaming for clarity.
- Both `main.py` and `voice.py` reference model `gpt-5.4`, which should be confirmed as an available model name in your OpenAI account before deployment.
- Error handling in `voice.py`'s `plan_trip` returns the raw exception message to the user (`f"An error occurred while planning the trip: {e}"`) — consider replacing this with a friendlier, non-technical message for production use.
