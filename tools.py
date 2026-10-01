"""여행 정보 도구.

Google ADK는 타입 힌트와 docstring이 있는 일반 Python 함수를 도구로
등록한다. 각 도구는 한 가지 일만 하고, mock_api의 원본 응답(코드,
unix timestamp, 최소 화폐 단위, 10배 정수)을 사람이 읽을 문자열로 바꾼다.
실패해도 예외를 던지지 않고 "[오류] ..."로 시작하는 안내 문자열을 돌려주어
에이전트가 사용자에게 다시 물어볼 수 있게 한다.
"""

from datetime import date as Date
from datetime import datetime, timezone

import mock_api

_WMO_KO = {
    0: "맑음",
    1: "대체로 맑음",
    3: "흐림",
    45: "안개",
    61: "비",
    63: "비 많음",
    71: "눈",
    80: "소나기",
}

# 사용자가 한국어로 도시를 말해도 찾을 수 있도록 한 별칭.
_CITY_ALIASES_KO = {
    "서울": "SEL", "인천": "SEL", "김포": "SEL",
    "도쿄": "TYO", "동경": "TYO",
    "오사카": "OSA",
    "파리": "PAR",
    "로마": "ROM",
    "바르셀로나": "BCN",
    "뉴욕": "NYC",
    "방콕": "BKK",
}
_CITY_NAMES_KO = {
    "SEL": "서울", "TYO": "도쿄", "OSA": "오사카", "PAR": "파리",
    "ROM": "로마", "BCN": "바르셀로나", "NYC": "뉴욕", "BKK": "방콕",
}

_CATEGORY_ALIASES = {
    "att": "att", "attraction": "att", "sightseeing": "att", "관광지": "att", "관광": "att", "명소": "att",
    "food": "food", "restaurant": "food", "음식점": "food", "맛집": "food", "식당": "food", "음식": "food",
    "muse": "muse", "museum": "muse", "박물관": "muse", "미술관": "muse",
    "shop": "shop", "shopping": "shop", "쇼핑": "shop",
}
_CATEGORY_KO = {"att": "관광지", "food": "음식점", "muse": "박물관", "shop": "쇼핑"}

_CABIN_KO = {"E": "이코노미", "B": "비즈니스"}

# mock_api의 금액은 최소 화폐 단위(1/100)로 온다.
_MINOR_PER_UNIT = 100


class _ToolInputError(ValueError):
    """사용자에게 그대로 보여줄 수 있는 입력 오류."""


def _supported_cities() -> str:
    return ", ".join(
        f"{_CITY_NAMES_KO[code]}({city['nm']}, {code}/{city['apt']})"
        for code, city in mock_api.CITIES.items()
    )


def _resolve_city(query: str) -> dict:
    """도시 이름(한/영)·도시 코드·공항 코드를 mock_api 도시 정보 하나로 바꾼다."""
    q = str(query or "").strip()
    if not q:
        raise _ToolInputError("도시가 비어 있습니다.")
    q = _CITY_ALIASES_KO.get(q, q)

    hits = mock_api.search_city(q)
    if not hits:
        raise _ToolInputError(f"'{query}' 도시를 찾지 못했습니다. 지원 도시: {_supported_cities()}")

    exact = [
        h for h in hits
        if q.lower() in (h["code"].lower(), h["apt"].lower(), h["nm"].lower())
    ]
    if len(exact) == 1:
        return exact[0]
    if len(hits) == 1:
        return hits[0]
    names = ", ".join(f"{h['nm']}({h['code']})" for h in hits)
    raise _ToolInputError(f"'{query}'에 해당하는 도시가 여러 곳입니다: {names}. 하나를 지정해 주세요.")


def _city_label(city: dict) -> str:
    return f"{_CITY_NAMES_KO.get(city['code'], city['nm'])}({city['nm']})"


def _parse_date(value: str, field: str = "날짜") -> Date:
    """YYYY-MM-DD 문자열을 검증해 date로 바꾼다."""
    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d").date()
    except ValueError:
        raise _ToolInputError(
            f"{field} '{value}'이(가) 올바르지 않습니다. 실제로 존재하는 날짜를 YYYY-MM-DD 형식으로 입력해 주세요."
        ) from None


def _require_not_past(day: Date, field: str) -> None:
    if day < Date.today():
        raise _ToolInputError(
            f"{field} {day.isoformat()}은(는) 이미 지난 날짜입니다(오늘: {Date.today().isoformat()})."
        )


def _won(minor: int) -> str:
    """최소 화폐 단위 금액을 '123,000원'으로 바꾼다."""
    return f"{minor // _MINOR_PER_UNIT:,}원"


def _clock(epoch: int) -> datetime:
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def _duration(seconds: int) -> str:
    hours, minutes = divmod(seconds // 60, 60)
    return f"{hours}시간 {minutes}분" if minutes else f"{hours}시간"


def _error(message: str) -> str:
    return f"[오류] {message}"


def get_weather(city: str, date: str) -> str:
    """특정 도시의 특정 날짜 날씨(날씨 상태, 최저~최고 기온, 강수확률, 풍속)를 조회한다.

    Args:
        city: 도시 이름(예: "Paris", "파리"), 도시 코드(예: "PAR") 또는 공항 코드(예: "CDG").
        date: 조회할 날짜. YYYY-MM-DD 형식(예: "2026-11-03").

    Returns:
        "파리(Paris) 2026-11-03(화): 맑음, 12.3~18.0℃, 강수확률 20%, 바람 3.4m/s" 형태의 문자열.
        도시를 못 찾거나 날짜가 잘못되면 "[오류]"로 시작하는 안내 문자열.
    """
    try:
        found = _resolve_city(city)
        day = _parse_date(date)
        weather = mock_api.fetch_weather(found["code"], day.isoformat())
    except (LookupError, ValueError) as error:
        return _error(str(error))

    return (
        f"{_city_label(found)} {day.isoformat()}({'월화수목금토일'[day.weekday()]}): "
        f"{_WMO_KO.get(weather['wmo'], '알 수 없음')}, "
        f"{weather['tmin_cx10'] / 10:.1f}~{weather['tmax_cx10'] / 10:.1f}℃, "
        f"강수확률 {weather['pop_pct']}%, 바람 {weather['wind_ms_x10'] / 10:.1f}m/s"
    )


def get_flights(departure: str, arrival: str, date: str) -> str:
    """출발 도시에서 도착 도시로 가는 특정 날짜의 편도 항공편 후보를 가격 낮은 순으로 조회한다.

    왕복이 필요하면 가는 편과 오는 편을 각각 한 번씩 호출한다.

    Args:
        departure: 출발 도시 이름(예: "Seoul", "서울"), 도시 코드(예: "SEL") 또는 공항 코드(예: "ICN").
        arrival: 도착 도시. departure와 같은 형식.
        date: 출발 날짜. YYYY-MM-DD 형식이며 오늘 이후여야 한다.

    Returns:
        항공편별 편명, 좌석 등급, 출발·도착 시각(UTC 기준), 비행 시간, 직항/경유, 1인 가격(원), 잔여 좌석을
        한 줄씩 담은 문자열. 입력이 잘못되면 "[오류]"로 시작하는 안내 문자열.
    """
    try:
        src = _resolve_city(departure)
        dst = _resolve_city(arrival)
        if src["code"] == dst["code"]:
            raise _ToolInputError("출발지와 도착지가 같습니다. 서로 다른 도시를 입력해 주세요.")
        day = _parse_date(date, "출발 날짜")
        _require_not_past(day, "출발 날짜")
        flights = mock_api.fetch_flights(src["apt"], dst["apt"], day.isoformat())
    except (LookupError, ValueError) as error:
        return _error(str(error))

    if not flights:
        return f"{_city_label(src)} → {_city_label(dst)} {day.isoformat()} 항공편이 없습니다."

    lines = [
        f"{_city_label(src)} {src['apt']} → {_city_label(dst)} {dst['apt']}, "
        f"{day.isoformat()} 항공편 {len(flights)}개 (가격 낮은 순, 시각은 UTC 기준, 가격은 1인 편도):"
    ]
    for i, f in enumerate(sorted(flights, key=lambda f: f["price_minor"]), start=1):
        dep, arr = _clock(f["dep"]), _clock(f["arr"])
        day_shift = (arr.date() - dep.date()).days
        arrival_text = arr.strftime("%H:%M") + (f"(+{day_shift}일)" if day_shift else "")
        stops = "직항" if f["stops"] == 0 else f"{f['stops']}회 경유"
        lines.append(
            f"{i}. {f['fno']} {_CABIN_KO.get(f['cls'], f['cls'])} | "
            f"{dep.strftime('%m-%d %H:%M')} 출발 → {arrival_text} 도착 "
            f"({_duration(f['arr'] - f['dep'])}, {stops}) | "
            f"{_won(f['price_minor'])} | 잔여 {f['seats']}석"
        )
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시의 숙소 후보를 체크인~체크아웃 기간 기준으로 조회한다. 예약 가능한 숙소를 가격 낮은 순으로 먼저 보여준다.

    Args:
        city: 도시 이름(예: "Paris", "파리"), 도시 코드(예: "PAR") 또는 공항 코드(예: "CDG").
        checkin: 체크인 날짜. YYYY-MM-DD 형식이며 오늘 이후여야 한다.
        checkout: 체크아웃 날짜. YYYY-MM-DD 형식이며 checkin보다 뒤여야 한다.

    Returns:
        숙소별 이름, 등급(성급), 1박 가격, 숙박 기간 총액(원, 객실 1개 기준), 도심까지 거리, 예약 가능 여부를
        한 줄씩 담은 문자열. 입력이 잘못되면 "[오류]"로 시작하는 안내 문자열.
    """
    try:
        found = _resolve_city(city)
        start = _parse_date(checkin, "체크인 날짜")
        end = _parse_date(checkout, "체크아웃 날짜")
        _require_not_past(start, "체크인 날짜")
        if end <= start:
            raise _ToolInputError(
                f"체크아웃({end.isoformat()})은 체크인({start.isoformat()})보다 뒤여야 합니다."
            )
        hotels = mock_api.fetch_hotels(found["code"], start.isoformat(), end.isoformat())
    except (LookupError, ValueError) as error:
        return _error(str(error))

    nights = (end - start).days
    hotels = sorted(hotels, key=lambda h: (not h["avail"], h["price_minor_night"]))
    available = sum(h["avail"] for h in hotels)
    lines = [
        f"{_city_label(found)} 숙소 {len(hotels)}곳 (예약 가능 {available}곳), "
        f"{start.isoformat()} 체크인 ~ {end.isoformat()} 체크아웃, {nights}박:"
    ]
    for i, h in enumerate(hotels, start=1):
        distance = f"{h['dist_m'] / 1000:.1f}km" if h["dist_m"] >= 1000 else f"{h['dist_m']}m"
        lines.append(
            f"{i}. {h['nm']} [{h['hid']}] ({h['star']}성급) | 1박 {_won(h['price_minor_night'])}, "
            f"{nights}박 총 {_won(h['price_minor_night'] * nights)} | 도심까지 {distance} | "
            f"{'예약 가능' if h['avail'] else '예약 불가(만실)'}"
        )
    if not available:
        lines.append("예약 가능한 숙소가 없습니다. 날짜를 바꿔 다시 조회해 보세요.")
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 한 카테고리 장소 후보(평점, 운영 시간, 입장료)를 평점 높은 순으로 조회한다.

    Args:
        city: 도시 이름(예: "Paris", "파리"), 도시 코드(예: "PAR") 또는 공항 코드(예: "CDG").
        category: 다음 중 하나. "att"(관광지), "food"(음식점), "muse"(박물관), "shop"(쇼핑).
            "관광지", "맛집", "박물관", "쇼핑" 같은 한국어 이름도 받는다.

    Returns:
        장소별 이름, 평점(5점 만점)과 리뷰 수, 운영 시간, 1인 입장료 또는 기본 요금(원 또는 무료)을 한 줄씩 담은 문자열.
        입력이 잘못되면 "[오류]"로 시작하는 안내 문자열.
    """
    cat = _CATEGORY_ALIASES.get(str(category or "").strip().lower())
    if cat is None:
        return _error(
            f"알 수 없는 카테고리 '{category}'입니다. att(관광지), food(음식점), muse(박물관), shop(쇼핑) 중 하나를 쓰세요."
        )
    try:
        found = _resolve_city(city)
        places = mock_api.fetch_places(found["code"], cat)
    except (LookupError, ValueError) as error:
        return _error(str(error))

    fee_label = "입장료" if cat in ("att", "muse") else "기본 요금"
    lines = [f"{_city_label(found)} {_CATEGORY_KO[cat]} {len(places)}곳 (평점 높은 순, 요금은 1인 기준):"]
    for i, p in enumerate(sorted(places, key=lambda p: -p["rating_x10"]), start=1):
        fee = "무료" if p["fee_minor"] == 0 else _won(p["fee_minor"])
        lines.append(
            f"{i}. {p['nm']} | 평점 {p['rating_x10'] / 10:.1f}/5 (리뷰 {p['reviews']:,}개) | "
            f"운영 {p['open_h']:02d}:00~{p['close_h']:02d}:00 | {fee_label} {fee}"
        )
    return "\n".join(lines)


def calculate_budget(
    flight_prices_krw: list[int],
    hotel_total_krw: int,
    entrance_fees_krw: list[int],
    travelers: int,
    daily_extra_krw: int,
    days: int,
) -> str:
    """여행 총예산을 정확히 합산한다. 일정 마지막의 예산 표를 만들기 전에 반드시 호출한다.

    모든 금액은 원 단위 정수다(예: 210000). 다른 도구가 보여준 가격을 그대로 옮겨 넣는다.

    Args:
        flight_prices_krw: 선택한 항공편들의 1인 가격 목록(예: 가는 편, 오는 편 → [210000, 250000]).
        hotel_total_krw: 선택한 숙소의 숙박 기간 총액(객실 1개 기준, 여러 숙소면 합계). 없으면 0.
        entrance_fees_krw: 일정에 넣은 장소들의 1인 입장료·기본 요금 목록. 무료는 0 또는 생략. 없으면 [].
        travelers: 여행 인원 수(1 이상).
        daily_extra_krw: 1인 1일 기타 경비(식비·교통비 등) 추정치. 모르면 0.
        days: 여행 일수(1 이상).

    Returns:
        항목별 금액과 총액, 1인당 금액을 담은 문자열. 입력이 잘못되면 "[오류]"로 시작하는 안내 문자열.
    """
    amounts = [*flight_prices_krw, hotel_total_krw, *entrance_fees_krw, daily_extra_krw]
    if travelers < 1 or days < 1:
        return _error("travelers와 days는 1 이상이어야 합니다.")
    if any(a < 0 for a in amounts):
        return _error("금액은 0 이상이어야 합니다.")

    flights = sum(flight_prices_krw) * travelers
    fees = sum(entrance_fees_krw) * travelers
    extra = daily_extra_krw * travelers * days
    total = flights + hotel_total_krw + fees + extra
    return "\n".join([
        f"예산 합계 ({travelers}명, {days}일):",
        f"- 항공: {flights:,}원 (1인 {sum(flight_prices_krw):,}원 × {travelers}명)",
        f"- 숙소: {hotel_total_krw:,}원",
        f"- 입장료: {fees:,}원 (1인 {sum(entrance_fees_krw):,}원 × {travelers}명)",
        f"- 기타 경비(추정): {extra:,}원 (1인 1일 {daily_extra_krw:,}원 × {travelers}명 × {days}일)",
        f"- 총액: {total:,}원 (1인당 약 {total // travelers:,}원)",
    ])
