"""여행 정보 도구 스켈레톤.

Google ADK는 타입 힌트와 docstring이 있는 일반 Python 함수를 도구로
등록한다. 아래 get_weather를 예시로 삼아 나머지 도구를 완성한다.
"""

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

_CATEGORY_KO = {"att": "관광지", "food": "음식점", "muse": "박물관", "shop": "쇼핑"}
_AIRPORT_TO_CITY = {city["apt"]: {"code": code, **city} for code, city in mock_api.CITIES.items()}


def _find_city(value: str) -> dict | None:
    """도시 이름·도시 코드·공항 코드로 도시를 찾는다."""
    hits = mock_api.search_city(value)
    if hits:
        return hits[0]
    return _AIRPORT_TO_CITY.get(str(value).strip().upper())


def _won(minor_units: int) -> str:
    """KRW 최소 단위를 정수 원화로 표시한다."""
    return f"₩{minor_units // 100:,}"


def _date_time(timestamp: int) -> str:
    """Unix timestamp를 한국 시간으로 표시한다."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def get_weather(city: str, date: str) -> str:
    """특정 도시의 특정 날짜 날씨를 조회한다.

    city는 도시 이름(예: Paris), 도시 코드(예: PAR), 공항 코드(예: CDG)
    중 하나이고 date는 YYYY-MM-DD 형식이어야 한다.
    """
    found = _find_city(city)
    if not found:
        return f"'{city}' 도시를 찾지 못했습니다."

    try:
        weather = mock_api.fetch_weather(found["code"], date)
    except (LookupError, ValueError) as error:
        return f"요청을 처리하지 못했습니다: {error}"
    return (
        f"{found['nm']} {date}: {_WMO_KO.get(weather['wmo'], '알 수 없음')}, "
        f"{weather['tmin_cx10'] / 10:.1f}~{weather['tmax_cx10'] / 10:.1f}℃, "
        f"강수확률 {weather['pop_pct']}%"
    )


def get_flights(departure: str, arrival: str, date: str) -> str:
    """출발지·도착지와 날짜(YYYY-MM-DD)의 항공편 후보를 조회한다.

    departure와 arrival에는 도시 이름, 도시 코드 또는 공항 코드를 사용할 수
    있다. mock_api.fetch_flights의 원본 응답을 사람이 읽기 좋은 문자열로
    변환하는 것이 이 도구의 TODO다.
    """
    src, dst = _find_city(departure), _find_city(arrival)
    if not src:
        return f"출발 도시 '{departure}'를 찾지 못했습니다."
    if not dst:
        return f"도착 도시 '{arrival}'를 찾지 못했습니다."
    try:
        flights = mock_api.fetch_flights(src["apt"], dst["apt"], date)
    except (LookupError, ValueError) as error:
        return f"항공편 요청을 처리하지 못했습니다: {error}"
    if not flights:
        return f"{src['nm']}에서 {dst['nm']}까지 {date} 항공편이 없습니다."
    lines = [f"{src['nm']}({src['apt']}) → {dst['nm']}({dst['apt']}), {date} 항공편 후보:"]
    for flight in flights:
        stops = "직항" if flight["stops"] == 0 else f"경유 {flight['stops']}회"
        cabin = "비즈니스석" if flight["cls"] == "B" else "일반석"
        lines.append(
            f"- {flight['fno']} ({cabin}, {stops}): "
            f"출발 {_date_time(flight['dep'])}, 도착 {_date_time(flight['arr'])}; "
            f"{_won(flight['price_minor'])}, 잔여 {flight['seats']}석"
        )
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    mock_api.fetch_hotels의 가격(원화 최소 단위), 숙박 일수, 이용 가능 여부를
    사람이 읽기 좋은 문자열로 변환하는 것이 이 도구의 TODO다.
    """
    found = _find_city(city)
    if not found:
        return f"'{city}' 도시를 찾지 못했습니다."
    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as error:
        return f"숙소 요청을 처리하지 못했습니다: {error}"
    if not hotels:
        return f"{found['nm']}의 {checkin}~{checkout} 숙소 후보가 없습니다."
    lines = [f"{found['nm']} 숙소 후보 ({checkin} 체크인, {checkout} 체크아웃):"]
    for hotel in hotels:
        total = hotel["price_minor_night"] * hotel["nights"]
        availability = "예약 가능" if hotel["avail"] else "예약 불가"
        lines.append(
            f"- {hotel['nm']} ({hotel['star']}성, {availability}): "
            f"1박 {_won(hotel['price_minor_night'])}, {hotel['nights']}박 총 {_won(total)}; "
            f"중심지에서 {hotel['dist_m']:,}m"
        )
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    mock_api.fetch_places의 평점·운영 시간·입장료를 사람이 읽기 좋은 문자열로
    변환하는 것이 이 도구의 TODO다.
    """
    found = _find_city(city)
    if not found:
        return f"'{city}' 도시를 찾지 못했습니다."
    cat = str(category).strip().lower()
    try:
        places = mock_api.fetch_places(found["code"], cat)
    except (LookupError, ValueError) as error:
        return f"장소 요청을 처리하지 못했습니다: {error}"
    label = _CATEGORY_KO.get(cat, cat)
    lines = [f"{found['nm']} {label} 후보:"]
    for place in places:
        fee = "무료" if place["fee_minor"] == 0 else _won(place["fee_minor"])
        lines.append(
            f"- {place['nm']}: 평점 {place['rating_x10'] / 10:.1f}/5 "
            f"({place['reviews']:,}개 리뷰), 운영 {place['open_h']:02d}:00~{place['close_h']:02d}:00, "
            f"입장료 {fee}"
        )
    return "\n".join(lines)
