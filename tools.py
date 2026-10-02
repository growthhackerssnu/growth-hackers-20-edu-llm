"""Google ADK 여행 정보 도구."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

import mock_api

_WMO_KO = {0: "맑음", 1: "대체로 맑음", 3: "흐림", 45: "안개", 61: "비", 63: "비가 많음", 71: "눈", 80: "소나기"}
_CABIN_KO = {"E": "이코노미", "B": "비즈니스"}
_CATEGORY_KO = {"att": "관광지", "food": "맛집", "muse": "박물관", "shop": "쇼핑"}
_MINOR_SCALE = Decimal("100")


def _city(value: str) -> dict[str, Any] | None:
    """도시명, 도시 코드, 공항 코드로 첫 일치 도시를 찾는다."""
    if not isinstance(value, str) or not value.strip():
        return None
    hits = mock_api.search_city(value)
    return hits[0] if hits else None


def _date(value: str) -> datetime | None:
    """정확한 YYYY-MM-DD 형식만 파싱한다."""
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return None
    return parsed if parsed.strftime("%Y-%m-%d") == value else None


def _city_label(city: dict[str, Any]) -> str:
    """도시명과 도시·공항 코드를 함께 표시한다."""
    return f"{city['nm']} ({city['code']} / {city['apt']})"


def _time(value: Any) -> str:
    """UNIX timestamp를 UTC 날짜·시각으로 표시한다."""
    try:
        return datetime.fromtimestamp(int(value), timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    except (OverflowError, OSError, TypeError, ValueError):
        return "시간 정보 없음"


def _money(minor: Any, currency: Any) -> str:
    """mock API의 minor-unit 금액을 읽기 쉬운 통화 금액으로 바꾼다."""
    try:
        amount = Decimal(str(minor)) / _MINOR_SCALE
    except (InvalidOperation, TypeError, ValueError):
        return "요금 정보 없음"
    number = f"{amount:,.0f}" if amount == amount.to_integral_value() else f"{amount:,.2f}"
    return f"{number}원 (KRW)" if str(currency).upper() == "KRW" else f"{currency} {number}"


def _error_city(value: Any) -> str:
    return f"'{value}' 도시를 찾지 못했습니다. 도시명, 도시 코드 또는 공항 코드를 확인해 주세요."


def get_weather(city: str, date: str) -> str:
    """도시의 일별 날씨를 조회한다.

    Args:
        city: 도시명, 도시 코드, 또는 공항 코드.
        date: YYYY-MM-DD 형식의 날짜.

    Returns:
        날씨, 기온, 강수확률 또는 안전한 오류 안내.
    """
    found = _city(city)
    if not found:
        return _error_city(city)
    if not _date(date):
        return "날짜는 YYYY-MM-DD 형식으로 입력해 주세요."
    try:
        item = mock_api.fetch_weather(found["code"], date)
        low, high = int(item["tmin_cx10"]) / 10, int(item["tmax_cx10"]) / 10
    except (KeyError, LookupError, TypeError, ValueError):
        return "날씨 정보를 가져오지 못했습니다. 도시와 날짜를 확인해 주세요."
    return f"[모의 API] {_city_label(found)} | {date}: {_WMO_KO.get(item.get('wmo'), '정보 없음')}, {low:.1f}~{high:.1f} C, 강수확률 {item.get('pop_pct', 0)}%"


def get_flights(departure: str, arrival: str, date: str) -> str:
    """출발지·도착지와 날짜의 항공편을 조회한다.

    Args:
        departure: 출발 도시명, 도시 코드, 또는 공항 코드.
        arrival: 도착 도시명, 도시 코드, 또는 공항 코드.
        date: YYYY-MM-DD 형식의 출발 날짜.

    Returns:
        UTC 시간, 좌석 등급, 요금, 경유와 잔여 좌석을 포함한 항공편 목록.
    """
    source, destination = _city(departure), _city(arrival)
    if not source:
        return _error_city(departure)
    if not destination:
        return _error_city(arrival)
    if not _date(date):
        return "출발 날짜는 YYYY-MM-DD 형식으로 입력해 주세요."
    if source["apt"] == destination["apt"]:
        return "출발지와 도착지는 서로 다른 도시로 입력해 주세요."
    try:
        flights = mock_api.fetch_flights(source["apt"], destination["apt"], date)
    except (LookupError, TypeError, ValueError):
        return "항공편 정보를 가져오지 못했습니다. 도시와 날짜를 확인해 주세요."
    if not flights:
        return "해당 조건의 항공편 데이터가 없습니다. 날짜 또는 도시를 바꿔 보세요."

    lines = [f"[모의 API] {_city_label(source)} -> {_city_label(destination)} | {date} 항공편 {len(flights)}건"]
    for index, item in enumerate(flights, 1):
        stops = int(item.get("stops", 0))
        stop_text = "직항" if stops == 0 else f"경유 {stops}회"
        lines.append(f"{index}. {item.get('fno', '편명 정보 없음')} | {_CABIN_KO.get(item.get('cls'), '등급 정보 없음')} | {_money(item.get('price_minor'), item.get('cur'))} | {stop_text} | 잔여 {item.get('seats', '?')}석")
        lines.append(f"   출발 {_time(item.get('dep'))} -> 도착 {_time(item.get('arr'))}")
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 숙박 기간에 맞는 숙소를 조회한다.

    Args:
        city: 도시명, 도시 코드, 또는 공항 코드.
        checkin: YYYY-MM-DD 형식의 체크인 날짜.
        checkout: YYYY-MM-DD 형식의 체크아웃 날짜.

    Returns:
        숙소별 성급, 1박·전체 요금, 거리와 예약 가능 여부.
    """
    found = _city(city)
    start, end = _date(checkin), _date(checkout)
    if not found:
        return _error_city(city)
    if not start or not end:
        return "체크인과 체크아웃 날짜는 YYYY-MM-DD 형식으로 입력해 주세요."
    nights = (end - start).days
    if nights <= 0:
        return "체크아웃 날짜는 체크인 날짜보다 뒤여야 합니다."
    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, TypeError, ValueError):
        return "숙소 정보를 가져오지 못했습니다. 도시와 날짜를 확인해 주세요."
    if not hotels:
        return "해당 조건의 숙소 데이터가 없습니다. 날짜 또는 도시를 바꿔 보세요."

    lines = [f"[모의 API] {_city_label(found)} | {checkin}~{checkout} ({nights}박) 숙소 {len(hotels)}곳"]
    for index, item in enumerate(hotels, 1):
        nightly = item.get("price_minor_night")
        try:
            total = int(nightly) * nights
        except (TypeError, ValueError):
            total = None
        distance = int(item.get("dist_m", 0))
        distance_text = f"{distance:,}m" if distance < 1000 else f"{distance / 1000:.1f}km"
        available = "예약 가능" if item.get("avail") else "매진 또는 예약 불가"
        lines.append(f"{index}. {item.get('nm', '숙소명 정보 없음')} | {item.get('star', '?')}성 | 1박 {_money(nightly, item.get('cur'))} | 총 {_money(total, item.get('cur'))} | 도심 {distance_text} | {available}")
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 관광지·맛집·박물관·쇼핑 장소를 조회한다.

    Args:
        city: 도시명, 도시 코드, 또는 공항 코드.
        category: att, food, muse, shop 중 하나.

    Returns:
        평점, 리뷰 수, 영업 시간, 입장료를 포함한 장소 목록.
    """
    found = _city(city)
    if not found:
        return _error_city(city)
    if not isinstance(category, str) or category.strip().lower() not in _CATEGORY_KO:
        options = ", ".join(f"{code}({name})" for code, name in _CATEGORY_KO.items())
        return f"장소 유형은 다음 중 하나로 입력해 주세요: {options}."
    code = category.strip().lower()
    try:
        places = mock_api.fetch_places(found["code"], code)
    except (LookupError, TypeError, ValueError):
        return "장소 정보를 가져오지 못했습니다. 도시와 장소 유형을 확인해 주세요."
    if not places:
        return "해당 조건의 장소 데이터가 없습니다. 도시 또는 장소 유형을 바꿔 보세요."

    lines = [f"[모의 API] {_city_label(found)} | {_CATEGORY_KO[code]} {len(places)}곳"]
    for index, item in enumerate(places, 1):
        fee = "무료" if item.get("fee_minor") == 0 else _money(item.get("fee_minor"), item.get("cur"))
        lines.append(f"{index}. {item.get('nm', '장소명 정보 없음')} | 평점 {int(item.get('rating_x10', 0)) / 10:.1f}/5 (리뷰 {int(item.get('reviews', 0)):,}개) | {int(item.get('open_h', 0)):02d}:00~{int(item.get('close_h', 0)):02d}:00 | 입장료 {fee}")
    return "\n".join(lines)
