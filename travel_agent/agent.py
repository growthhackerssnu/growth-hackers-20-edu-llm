"""Google ADK web playground entry point for the travel itinerary agent."""

import os

from dotenv import load_dotenv
from google.adk.agents import Agent

from prompts import SYSTEM_PROMPT
from tools import get_flights, get_hotels, get_places, get_weather

load_dotenv()

MODEL = os.getenv("GOOGLE_MODEL", "gemini-3.6-flash").strip() or "gemini-3.6-flash"

root_agent = Agent(
    name="travel_agent",
    model=MODEL,
    description="모의 여행 정보를 확인해 날짜별 여행 일정 초안을 만드는 에이전트",
    instruction=SYSTEM_PROMPT,
    tools=[get_weather, get_flights, get_hotels, get_places],
)
