"""툴 등록기. 수정하지 마세요.

함수 위에 @tool 을 붙이면 OpenAI 가 요구하는 JSON 스키마가 자동으로 만들어집니다.
스키마는 함수 이름 + 파라미터 타입힌트 + docstring 에서 나옵니다.
즉 docstring 은 주석이 아니라 LLM 이 실제로 읽는 설명서입니다.
"""

import inspect
import typing

TOOLS = {}  # 이름 -> {"fn": 함수, "schema": OpenAI 툴 스키마}

_JSON_TYPES = {str: "string", int: "integer", float: "number", bool: "boolean"}


def tool(fn):
    """함수를 LLM 툴로 등록한다."""
    doc = inspect.getdoc(fn)
    if not doc:
        raise ValueError(f"{fn.__name__}: docstring 이 필요합니다. LLM 이 이 설명을 보고 툴을 고릅니다.")

    hints = typing.get_type_hints(fn)
    params = {
        name: {"type": _JSON_TYPES.get(hints.get(name), "string")}
        for name in inspect.signature(fn).parameters
    }

    TOOLS[fn.__name__] = {
        "fn": fn,
        "schema": {
            "type": "function",
            "function": {
                "name": fn.__name__,
                "description": doc,
                "parameters": {
                    "type": "object",
                    "properties": params,
                    "required": list(params),
                },
            },
        },
    }
    return fn
