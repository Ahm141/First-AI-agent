import logging
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    RoomInputOptions,
    WorkerOptions,
    cli,
    function_tool,
)
from livekit.plugins import openai as lk_openai
from livekit.plugins import silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel
from agents import Runner
from main import travel_agent

load_dotenv(override=True)

logger = logging.getLogger("voice-travel-agent")


class VoiceTravelAssistant(Agent):


    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a friendly travel assistant talking to the user by "
                "voice, like a phone call. Speak in short, natural sentences "
                "suitable for spoken conversation, not like written text or "
                "a report. If the user asks you to plan a trip, estimate a "
                "cost, or give local tips, use the plan_trip tool right away "
                "instead of trying to answer from your own knowledge. Once "
                "you get the tool's result, summarize it conversationally "
                "for the user (don't just read the fields one by one like a form)."
            )
        )

    @function_tool()
    async def plan_trip(self, request: str) -> str:
       
        await self.session.say("One moment, let me check the best plan for you...")

        try:
            result = await Runner.run(travel_agent, request)
            output = result.final_output 
        except agents.exceptions.InputGuardrailTripwireTriggered:
            return (
                "The budget mentioned is unrealistic for the requested trip. "
                "Ask the user for a higher budget or a shorter duration."
            )
        except Exception as e:
            logger.exception("travel_agent failed")
            return f"An error occurred while planning the trip: {e}"

        
        return (
            f"Destination: {output.destination}. "
            f"Duration: {output.duration}. "
            f"Plan summary: {output.summary}. "
            f"Estimated cost: {output.cost}. "
            f"Local tips: {output.tips}."
        )


async def entrypoint(ctx: JobContext):
    await ctx.connect()

    session = AgentSession(
        stt=lk_openai.STT(),
        llm=lk_openai.LLM(model="gpt-4.1-mini"),
        tts=lk_openai.TTS(voice="onyx"),
        vad=silero.VAD.load(),
        turn_detection=MultilingualModel(),
        preemptive_generation=False,
        min_endpointing_delay=0.8,
    )

    await session.start(
        room=ctx.room,
        agent=VoiceTravelAssistant(),
        room_input_options=RoomInputOptions(),
    )

    await session.say("Hi! I'm Dan your travel assistant. Where would you like to go?")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))