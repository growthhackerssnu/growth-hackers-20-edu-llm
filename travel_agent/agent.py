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
    description="모의 여행 정보를 조회해 항공·숙소·장소·날씨를 반영한 일정을 제안하는 여행 어시스턴트",
    instruction=SYSTEM_PROMPT,
    tools=[get_weather, get_flights, get_hotels, get_places],
)
