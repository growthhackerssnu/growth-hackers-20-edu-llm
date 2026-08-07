"""여러분이 채울 파일 (1/2).

mock_api 가 주는 원본 데이터를 LLM 이 읽을 수 있는 문장으로 바꾸는 곳입니다.
아래 get_weather 가 완성된 예시입니다. 이 패턴을 보고 나머지를 직접 만드세요.

규칙
  - @tool 을 붙인 함수는 자동으로 LLM 이 쓸 수 있게 됩니다.
  - 파라미터에는 타입힌트를 붙이세요 (str / int / float / bool).
  - docstring 은 LLM 이 읽는 설명서입니다. 언제 쓰는 툴인지, 인자 형식이 뭔지 적으세요.
  - 반환값은 문자열입니다. 원본 dict 를 그대로 str() 해서 넘기지 마세요.
"""

import mock_api
from registry import tool

_WMO_KO = {0: "맑음", 1: "대체로 맑음", 3: "흐림", 45: "안개",
           61: "비", 63: "비 많음", 71: "눈", 80: "소나기"}


@tool
def get_weather(city: str, date: str) -> str:
    """특정 도시의 특정 날짜 날씨를 알려준다. city 는 도시 이름(예: Paris), date 는 YYYY-MM-DD 형식."""
    hits = mock_api.search_city(city)
    if not hits:
        return f"'{city}' 도시를 찾지 못했습니다. 다른 이름으로 물어보세요."

    found = hits[0]
    w = mock_api.fetch_weather(found["code"], date)
    return (
        f"{found['nm']} {date}: {_WMO_KO.get(w['wmo'], '알 수 없음')}, "
        f"{w['tmin_cx10'] / 10:.1f}~{w['tmax_cx10'] / 10:.1f}℃, "
        f"강수확률 {w['pop_pct']}%"
    )


# TODO: 툴을 최소 3개 더 만드세요.
#
# 쓸 수 있는 원본 함수 (자세한 형식은 mock_api.py 를 직접 읽어보세요):
#   mock_api.search_city(q)                          -> 도시 코드 찾기
#   mock_api.fetch_flights(apt_from, apt_to, date)   -> 항공편. 시간은 unix timestamp, 값은 원화 1/100 단위
#   mock_api.fetch_hotels(city_code, checkin, checkout)
#   mock_api.fetch_places(city_code, cat)            -> cat 은 att / food / muse / shop
#
# 만들면서 스스로 물어볼 것:
#   - 결과가 10개면 다 넘길 것인가, 골라서 3개만 넘길 것인가?
#   - 1756742400 이라는 숫자를 모델이 이해할까?
#   - 없는 도시를 물어보면 무슨 일이 일어나야 하나?
#   - 툴 하나가 너무 많은 걸 하고 있지는 않은가?
