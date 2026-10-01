"""Google ADK 웹 플레이그라운드용 여행 일정 에이전트."""

import os
from datetime import date

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext

from prompts import SYSTEM_PROMPT
from tools import calculate_budget, get_flights, get_hotels, get_places, get_weather

load_dotenv()

MODEL = os.getenv("GOOGLE_MODEL", "gemini-3.6-flash")


def build_instruction(context: ReadonlyContext) -> str:
    """요청마다 오늘 날짜를 붙여 상대적 날짜와 지난 날짜를 판단할 수 있게 한다."""
    today = date.today()
    weekday = "월화수목금토일"[today.weekday()]
    return f"{SYSTEM_PROMPT}\n\n# 오늘 날짜\n{today.isoformat()} ({weekday})"


root_agent = Agent(
    name="travel_agent",
    model=MODEL,
    description="항공편·숙소·날씨·장소를 조회해 일자별 여행 일정과 예산을 만드는 에이전트",
    instruction=build_instruction,
    tools=[get_weather, get_flights, get_hotels, get_places, calculate_budget],
)
