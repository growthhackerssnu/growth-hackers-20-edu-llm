"""Google ADK 웹 플레이그라운드용 여행 일정 에이전트."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from prompts import SYSTEM_PROMPT
from tools import get_flights, get_hotels, get_places, get_weather

load_dotenv()

MODEL = os.getenv("GOOGLE_MODEL", "gemini-3.6-flash")

root_agent = Agent(
    name="travel_agent",
    model=MODEL,
    description="여행 일정 에이전트 스켈레톤",
    instruction=SYSTEM_PROMPT,
    tools=[get_weather, get_flights, get_hotels, get_places],
)
