"""에이전트 루프. 수정하지 마세요.

LLM에게 묻는다 -> 툴을 부르라고 하면 부른다 -> 결과를 다시 넣는다 -> 답이 나올 때까지 반복.
에이전트라고 부르는 것의 전부가 이 40줄입니다.

  python agent.py "서울에서 파리 3일 일정 짜줘"
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

import tools  # noqa: F401  import 하는 것만으로 @tool 이 TOOLS 에 등록된다
from prompts import SYSTEM_PROMPT
from registry import TOOLS

load_dotenv()
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_STEPS = 8


def run(user_msg: str, history: list = None):
    """질문에 답한다. ("tool", 이름, 인자, 결과) 와 ("text", 답변) 을 순서대로 yield 한다."""
    client = OpenAI()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *(history or []),
        {"role": "user", "content": user_msg},
    ]
    schemas = [t["schema"] for t in TOOLS.values()]

    for _ in range(MAX_STEPS):
        msg = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=schemas or None,
        ).choices[0].message
        messages.append(msg)

        if not msg.tool_calls:
            yield ("text", msg.content or "")
            return

        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments or "{}")
            try:
                result = str(TOOLS[tc.function.name]["fn"](**args))
            except Exception as e:  # 툴이 깨져도 대화는 계속된다. 모델이 보고 판단한다.
                result = f"ERROR: {type(e).__name__}: {e}"
            yield ("tool", tc.function.name, args, result)
            messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})

    yield ("text", f"(툴을 {MAX_STEPS}번 부르고도 끝나지 않았습니다. 툴 설명이나 시스템 프롬프트를 다듬어 보세요.)")


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "서울에서 파리 3일 일정 짜줘"
    for ev in run(question):
        if ev[0] == "tool":
            print(f"🔧 {ev[1]}({ev[2]}) -> {ev[3][:300]}")
        else:
            print("\n" + ev[1])
