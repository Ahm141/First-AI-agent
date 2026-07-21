import os
import json
import asyncio
from openai import OpenAI
from dotenv import load_dotenv,find_dotenv
from agents import Agent , Runner , ModelSettings, WebSearchTool 
from pydantic import BaseModel , ValidationError

_ = load_dotenv(find_dotenv())

client = OpenAI(
api_key=os.environ["OPENAI_API_KEY"]
)

class TravelOutput(BaseModel):
    destination: str
    duration: str
    summary: str

travel_agent = Agent(
    name="Travel Agent",
    model="gpt-5",
    instructions=("You are frindly and knowledgeable  travel planning assistant. "
    "Your task is to create a detailed travel plan ." \
    "Use tools when helpful (e.g. , Web Search) "
    "The output should be structured as valid json format with the following fields:"
    " destination, duration, and summary. The summary should include key activities,"
    " local cuisine recommendations, and cultural experiences."),

    output_type=TravelOutput,
    model_settings=ModelSettings(
            reasoning={"effort": "medium"},
            extra_body={"text":{"verbosity":"low"}}
        ),
    tools=[
            WebSearchTool(search_context_size="low")
        ],
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

def input_travel_info():
    Travel_info = {
        "destination": input("Where do you want to go? "),
        "duration":(input("How long do you want to stay? ")),
        "budget": (input("What is your budget? ")),
        "purpose": (input("What is the purpose of your trip? "))
    }
    return Travel_info

async def main():
    Travel_info = input_travel_info()
    try:
        result = await Runner.run(travel_agent, f"Plan a {Travel_info['duration']} \
                                  trip to {Travel_info['destination']}\
                                      with a budget of ${Travel_info['budget']}.\
                                      purpose of the trip is {Travel_info['purpose']}. \
                                              Find uncommon places to visit."
        )
        print_travel_plan(result.final_output)
    except Exception as e:
        print("Error:", e)



if __name__ == "__main__":
    asyncio.run(main())
