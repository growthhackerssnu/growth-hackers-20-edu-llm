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


def get_weather(city: str, date: str) -> str:
    """특정 도시의 특정 날짜 날씨를 조회한다.

    city는 도시 이름(예: Paris), 도시 코드(예: PAR), 공항 코드(예: CDG)
    중 하나이고 date는 YYYY-MM-DD 형식이어야 한다.
    """
    hits = mock_api.search_city(city)
    if not hits:
        return f"'{city}' 도시를 찾지 못했습니다."

    found = hits[0]
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
    departure_city = _find_city(departure)
    arrival_city = _find_city(arrival)
    if departure_city is None or arrival_city is None:
        missing = departure if departure_city is None else arrival
        return f"'{missing}' 도시 또는 공항을 찾을 수 없습니다."

    try:
        flights = mock_api.fetch_flights(
            departure_city["apt"], arrival_city["apt"], date
        )
    except (LookupError, ValueError) as error:
        return f"항공편을 조회하지 못했습니다: {error}"

    if not flights:
        return f"{date} {departure_city['nm']} → {arrival_city['nm']} 항공편이 없습니다."

    lines = [f"{date} {departure_city['nm']} → {arrival_city['nm']} 항공편"]
    for flight in sorted(flights, key=lambda item: item["price_minor"]):
        departure_time = _format_timestamp(flight["dep"])
        arrival_time = _format_timestamp(flight["arr"])
        cabin = "비즈니스" if flight["cls"] == "B" else "이코노미"
        stops = "직항" if flight["stops"] == 0 else f"경유 {flight['stops']}회"
        lines.append(
            f"- {flight['fno']} | {departure_time} → {arrival_time} | "
            f"{cabin}, {stops} | {_format_money(flight['price_minor'], flight['cur'])} "
            f"| 잔여 {flight['seats']}석"
        )
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    mock_api.fetch_hotels의 가격(원화 최소 단위), 숙박 일수, 이용 가능 여부를
    사람이 읽기 좋은 문자열로 변환하는 것이 이 도구의 TODO다.
    """
    found = _find_city(city)
    if found is None:
        return f"'{city}' 도시를 찾을 수 없습니다."

    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as error:
        return f"숙소를 조회하지 못했습니다: {error}"

    available = [hotel for hotel in hotels if hotel["avail"]]
    if not available:
        return f"{checkin}~{checkout}에 예약 가능한 {found['nm']} 숙소가 없습니다."

    nights = available[0]["nights"]
    lines = [f"{found['nm']} 숙소 ({checkin}~{checkout}, {nights}박)"]
    for hotel in sorted(available, key=lambda item: item["price_minor_night"]):
        nightly = _format_money(hotel["price_minor_night"], hotel["cur"])
        total = _format_money(hotel["price_minor_night"] * nights, hotel["cur"])
        lines.append(
            f"- {hotel['nm']} | {'★' * hotel['star']} | 1박 {nightly}, "
            f"총 {total} | 중심가 약 {hotel['dist_m']:,}m"
        )
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    mock_api.fetch_places의 평점·운영 시간·입장료를 사람이 읽기 좋은 문자열로
    변환하는 것이 이 도구의 TODO다.
    """
    found = _find_city(city)
    if found is None:
        return f"'{city}' 도시를 찾을 수 없습니다."

    category_labels = {
        "att": "관광명소",
        "food": "음식점",
        "muse": "박물관",
        "shop": "쇼핑",
    }
    normalized_category = str(category).strip().lower()
    if normalized_category not in category_labels:
        choices = ", ".join(f"{code}({label})" for code, label in category_labels.items())
        return f"알 수 없는 카테고리 '{category}'입니다. 다음 중 하나를 사용하세요: {choices}."

    try:
        places = mock_api.fetch_places(found["code"], normalized_category)
    except LookupError as error:
        return f"장소를 조회하지 못했습니다: {error}"

    lines = [f"{found['nm']} {category_labels[normalized_category]}"]
    for place in sorted(places, key=lambda item: item["rating_x10"], reverse=True):
        fee = "무료" if place["fee_minor"] == 0 else _format_money(place["fee_minor"], place["cur"])
        lines.append(
            f"- {place['nm']} | 평점 {place['rating_x10'] / 10:.1f} "
            f"({place['reviews']:,}개 리뷰) | {place['open_h']:02d}:00~"
            f"{place['close_h']:02d}:00 | 입장 {fee}"
        )
    return "\n".join(lines)


def _find_city(query: str) -> dict | None:
    """Look up a city using its city name, city code, or airport code."""
    hits = mock_api.search_city(query)
    return hits[0] if hits else None


def _format_timestamp(epoch_seconds: int) -> str:
    """Render the mock API's UTC Unix timestamp as a concise date and time."""
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime("%m/%d %H:%M UTC")


def _format_money(minor: int, currency: str) -> str:
    """Convert a minor-unit integer to a human-readable currency amount."""
    amount = minor / 100
    if currency == "KRW":
        return f"KRW {amount:,.0f}"
    return f"{currency} {amount:,.2f}"
