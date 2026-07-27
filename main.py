import os
import json
import asyncio
from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
from agents import (Agent ,
                     Runner ,
                       ModelSettings,
                         WebSearchTool,
                          GuardrailFunctionOutput,
                           InputGuardrail,
                            InputGuardrailTripwireTriggered,
                             SQLiteSession )
from pydantic import BaseModel , ValidationError

_ = load_dotenv(find_dotenv(),override=True)

client = OpenAI(
api_key=os.environ["OPENAI_API_KEY"]
)

class TravelOutput(BaseModel):
    destination: str
    duration: str
    summary: str
    cost : str
    tips : str

class BudgetCheckOutput(BaseModel):
    is_valid: bool
    reasoning: str

budget_guardrail_agent = Agent(
    name="Budget Guardrail Agent",
    model="gpt-5.4",
    instructions=("Decide if the user's travel request includes an unrealistic budget."
    "if the budget is open, Consider it realistic" \
    "if the request says things obviously too low and Suggest the appropriate budget fo the trip" \
    "for the destinayion and duration, set is_valid to false and explain why in reasoning." \
    "Otherwise, set is_valid to true." \
    ),
    output_type=BudgetCheckOutput,
)

async def budget_guardrail(ctx, agent, input_data):
    result = await Runner.run(budget_guardrail_agent, input_data, context=ctx.context)
    final_output = result.final_output_as(BudgetCheckOutput)
    print("Budget guardrail reasoning:", final_output.reasoning)
    return GuardrailFunctionOutput(
         output_info = final_output,
                tripwire_triggered=not final_output.is_valid
    )
         
    


planner_agent = Agent(
    name= "Planner Agent",
    model="gpt-5.4",
    handoff_description=("Use me when the user needs plan or outline an itinerary , schedule ,or daily plan."
    ),
    instructions=("You spsecialize in creating day-by-day travel itineraries and sequencing activities. " \
    "Always return the output in valid json format with the following fields: destination, duration, summary, cost, and tips. " \
    ),
    model_settings=ModelSettings(
        reasoning={"effort": "low"},
        extra_body={"text":{"verbosity":"low"}}
    ),
    tools=[
        WebSearchTool()]
                  
)

budget_agent = Agent(
    name="Budget Agent",
    model="gpt-5.4",
    handoff_description=("Use me when the user needs mentions budget, price, cost, dollars, under $X,  or asks about expenses."
    ),
    instructions=("you estimate costs for lodging, food, transportation, and activities at a high level; flag budget violations. "
    "Always return JSON with structure: {\"cost\": \"string\"}. "
    ),
    model_settings=ModelSettings(
        reasoning={"effort": "low"},
        extra_body={"text":{"verbosity":"low"}}
    ),
    tools=[
        WebSearchTool()]
                  
)

local_guide_agent = Agent(
    name="Local Guide Agent",
    model="gpt-5.4",
    handoff_description=("Use me when the user ask for food, restaurants, neighborhoods, local tips, or 'what's good nearby'."
    ),
    instructions=("You provide restaurant, cultural, and current local highlights. "
    "Always return JSON with structure: {\"tips\": \"string\"}. "
    ),
    model_settings=ModelSettings(
        reasoning={"effort": "low"},
        extra_body={"text":{"verbosity":"low"}}
    ),
    tools=[
        WebSearchTool()
        ]
                  
)

travel_agent = Agent(
    name="Travel Agent",
    model="gpt-5.4",
    instructions=("You are frindly and knowledgeable helps users plan their trips, suggest destinations, and create detailed summaries of their journeys." \
    "You need to process requests more quickly and be precise in your responses.  "
    "Your primary role is to orchestrate other special agents(used as tools) to complete the user's request."
    "when planning a trip, call the **planner_agent** to create daily schedules, organize destinations, and recommend attractions or activities. Do not create itineraries yourself. "
    "when estimating costs, call the **budget_agent** to calculate the total cost including flights, hotels, and activities.Do not calculate costs yourself. "
    "when providing local tips, call the **local_guide_agent** to suggest restaurants, cultural experiences, and hidden gems. Do not generate local recommendations with this agent. "
    "use this agent one at a time in a logical order based on the request - first, call the planner_agent to create a travel plan, then call the budget_agent to estimate costs, and finally call the local_guide_agent to provide local tips. " \
    "After receiving results from these agents, compile their output into a single structured summary." \
    "Return JSON using this exact structure:"
    " {\"destination\": \"string\", \"duration\": \"string\", \"summary\": \"string\", \"cost\": \"string\", \"tips\": \"string\"}. "
    ),

    output_type=TravelOutput,
    model_settings=ModelSettings(
            reasoning={"effort": "low"},
            extra_body={"text":{"verbosity":"low"}}
        ),
    tools=[
            planner_agent.as_tool(
                tool_name="planner_agent",
                tool_description="plan or outline an itinerary, schedule, or daily plan."
            ),
            budget_agent.as_tool(
                tool_name="budget_agent",
                tool_description="calculate the cost of a trip."
            ),
            local_guide_agent.as_tool(
                tool_name="local_guide_agent",
                tool_description="provide restaurants, neighorhoods, cultural tips, and current local highlights."
            )
        ],
        input_guardrails=[
            InputGuardrail(guardrail_function=budget_guardrail)
        ]
)


def print_travel_plan(travel_plan: TravelOutput):
    if isinstance(travel_plan, str):
        try:
            travel_plan = TravelOutput(**json.loads(travel_plan))
        except (ValidationError, json.JSONDecodeError) as e:
            print("raw output:", travel_plan)
            return
        
    print("Travel Plan:")
    print(f"Destination: {travel_plan.destination}")
    print(f"Duration: {travel_plan.duration}")
    print(f"Summary: {travel_plan.summary}")
    print(f"Cost: {travel_plan.cost}")
    print(f"Tips: {travel_plan.tips}")

def input_travel_info():
    Travel_info = {
        "prompt": input("Hi I'm your travel assistant. How can I help you today? "),
    }
    return Travel_info

async def main():
    session = SQLiteSession ("travel_agent",db_path="travel_agent.sqlits")


    Travel_info = input_travel_info()
            
    try:
        result = await Runner.run(travel_agent, Travel_info["prompt"])
        print_travel_plan(result.final_output)
    except InputGuardrailTripwireTriggered as e:
        print("\n Guardrail blocked this budget:", e) 
           
    except Exception as e:
        print("Error:", e)



if __name__ == "__main__":
    asyncio.run(main())
