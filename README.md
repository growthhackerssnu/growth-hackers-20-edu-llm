# 여행 일정 에이전트 스켈레톤 (Google ADK)

Google Agent Development Kit(ADK)로 여행 일정 에이전트를 만드는 스켈레톤입니다. `get_weather`는 완성된 예시이고, 나머지 도구와 시스템 프롬프트를 직접 완성합니다. ADK 웹 플레이그라운드에서 대화 이력과 툴 호출을 확인할 수 있습니다.

## 실행 안내

준비물은 Python 3.10 이상과 `uv`입니다. 아래 명령으로 의존성과 로컬 환경을 준비합니다.

```bash
sh init.sh
```

`init.sh`는 `uv`가 없으면 설치하고, `uv sync`로 `google-adk`를 포함한 프로젝트 의존성을 설치합니다. `.env`가 없을 때는 `.env.example`에서 생성합니다.

`.env`를 열어 Google AI Studio에서 발급한 키를 넣으세요.

```dotenv
GOOGLE_API_KEY=여기에_키를_입력
GOOGLE_MODEL=gemini-3.6-flash
```

`GOOGLE_MODEL`을 생략하면 `travel_agent/agent.py`가 `gemini-3.6-flash`를 기본값으로 사용합니다.

`.env`에 Google AI Studio API 키를 넣은 뒤 ADK 웹 UI를 실행합니다.

```bash
uv run adk web .
```

터미널에 출력된 주소(일반적으로 `http://localhost:8000`)를 브라우저에서 열고 `travel_agent`를 선택해 대화하세요. 이 프로젝트에서는 `travel_agent/agent.py`의 `root_agent`가 ADK 앱의 진입점입니다. 종료는 실행한 터미널에서 `Ctrl+C`입니다.

8000번 포트가 사용 중이면 다른 포트를 지정할 수 있습니다.

```bash
uv run adk web . --port 8001
```

API 키 없이도 mock API 점검, 도구 import, 완성된 날씨 예시를 확인할 수 있습니다. 나머지 도구는 현재 TODO 문자열을 반환합니다.

```bash
uv run python mock_api.py
uv run python -m compileall -q tools.py prompts.py travel_agent mock_api.py
uv run python -c "from tools import get_weather; print(get_weather('Paris', '2026-09-01'))"
```

## 파일 지도

| 파일 | 내용 | 수정 |
|---|---|---|
| `travel_agent/agent.py` | ADK `root_agent`: 모델, 프롬프트, 툴을 연결 | △ |
| `tools.py` | ADK가 호출하는 여행 정보 함수. 날씨는 예시, 나머지는 TODO | ✓ |
| `prompts.py` | 에이전트 역할·규칙·출력 형식 TODO | ✓ |
| `mock_api.py` | 가짜 여행 API 원본 데이터 | ✗ |
| `init.sh` | uv 및 의존성 설치·환경 준비 | ✗ |

## 해야 할 일

1. `tools.py`의 `get_weather` 구현과 `mock_api.py`의 원본 응답을 읽으세요.
2. `get_flights`, `get_hotels`, `get_places`를 완성하세요. ADK 툴은 타입힌트와 docstring이 있는 일반 Python 함수입니다.
3. `prompts.py`에 역할, 툴 사용 규칙, 일정 출력 형식, 실패 처리를 작성하세요.
4. `travel_agent/agent.py`의 `tools=[...]` 목록은 이미 연결되어 있습니다. 도구를 추가하면 이 목록에도 연결하세요.
5. `uv run adk web .`에서 실제 대화를 해 보고 툴과 프롬프트를 다듬으세요.

## 제출 규칙

- `.env`는 제출하거나 Git에 추가하지 마세요.
- `tools.py`, `prompts.py`, `travel_agent/agent.py`의 변경 사항을 제출합니다.
- 필요하면 ADK 웹 UI의 데모 대화 로그를 함께 제출합니다.

## 평가 기준

| 항목 | 보는 것 |
|---|---|
| 툴 설계 | 툴이 한 가지 일을 명확히 하며 docstring만으로 사용법을 알 수 있는가 |
| 데이터 가공 | 코드·타임스탬프·최소 화폐 단위를 사람이 읽을 형식으로 바꾸는가 |
| 예외 처리 | 없는 도시나 잘못된 날짜에도 에이전트가 무너지지 않는가 |
| 프롬프트 | 툴을 제때 쓰고 사실을 지어내지 않으며 일정 형식이 일관적인가 |
| 결과 | 날짜 순서·이동·예산이 자연스러운가 |
