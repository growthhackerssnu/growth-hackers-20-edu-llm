"""여행 정보 도구."""

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


def _find_city(city: str) -> dict | None:
    """도시 이름, 도시 코드 또는 공항 코드로 도시 정보를 찾는다."""
    hits = mock_api.search_city(city)
    return hits[0] if hits else None


def _format_krw(amount_minor: int) -> str:
    """원화 최소 단위를 읽기 쉬운 원화로 변환한다."""
    return f"{amount_minor / 100:,.0f}원"


def _format_time(timestamp: int) -> str:
    """Unix timestamp를 UTC 기준 시:분으로 변환한다."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%H:%M")


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
        f"강수확률 {weather['pop_pct']}%, "
        f"풍속 {weather['wind_ms_x10'] / 10:.1f}m/s"
    )


def get_flights(departure: str, arrival: str, date: str) -> str:
    """출발지·도착지와 날짜(YYYY-MM-DD)의 항공편 후보를 조회한다.

    departure와 arrival에는 도시 이름, 도시 코드 또는 공항 코드를 사용할 수
    있다. 항공편 번호, 출·도착 시각, 좌석 등급, 가격, 경유 여부, 잔여 좌석을
    읽기 쉬운 형식으로 반환한다.
    """
    departure_city = _find_city(departure)
    arrival_city = _find_city(arrival)

    if not departure_city:
        return f"출발 도시 '{departure}'를 찾지 못했습니다."
    if not arrival_city:
        return f"도착 도시 '{arrival}'를 찾지 못했습니다."
    if departure_city["code"] == arrival_city["code"]:
        return "출발지와 도착지는 서로 다른 도시여야 합니다."

    try:
        flights = mock_api.fetch_flights(
            departure_city["apt"], arrival_city["apt"], date
        )
    except (LookupError, ValueError) as error:
        return f"항공편을 조회하지 못했습니다: {error}"

    class_name = {"E": "일반석", "B": "비즈니스석"}
    lines = [
        f"{departure_city['nm']}({departure_city['apt']}) → "
        f"{arrival_city['nm']}({arrival_city['apt']}) | {date} 항공편"
    ]

    for flight in sorted(flights, key=lambda item: item["price_minor"]):
        stops = "직항" if flight["stops"] == 0 else f"{flight['stops']}회 경유"
        lines.append(
            f"- {flight['fno']} | {_format_time(flight['dep'])} 출발 → "
            f"{_format_time(flight['arr'])} 도착 | "
            f"{class_name.get(flight['cls'], flight['cls'])} | "
            f"{stops} | {_format_krw(flight['price_minor'])} | "
            f"잔여 {flight['seats']}석"
        )

    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    이용 가능한 숙소의 등급, 1박 가격, 총 숙박 가격, 도심까지 거리와 숙박 일수를
    읽기 쉬운 형식으로 반환한다.
    """
    found = _find_city(city)
    if not found:
        return f"'{city}' 도시를 찾지 못했습니다."

    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as error:
        return f"숙소를 조회하지 못했습니다: {error}"

    available_hotels = [hotel for hotel in hotels if hotel["avail"]]
    if not available_hotels:
        return (
            f"{found['nm']} {checkin}~{checkout}에 예약 가능한 숙소를 "
            "찾지 못했습니다."
        )

    nights = available_hotels[0]["nights"]
    lines = [
        f"{found['nm']} 숙소 | {checkin}~{checkout} ({nights}박)"
    ]

    for hotel in sorted(available_hotels, key=lambda item: item["price_minor_night"]):
        total_price = hotel["price_minor_night"] * hotel["nights"]
        lines.append(
            f"- {hotel['nm']} | {hotel['star']}성 | "
            f"1박 {_format_krw(hotel['price_minor_night'])} "
            f"(총 {_format_krw(total_price)}) | "
            f"도심 약 {hotel['dist_m']:,}m"
        )

    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    한국어 카테고리도 사용할 수 있다. 장소의 평점, 리뷰 수, 운영 시간, 입장료를
    읽기 쉬운 형식으로 반환한다.
    """
    found = _find_city(city)
    if not found:
        return f"'{city}' 도시를 찾지 못했습니다."

    category_map = {
        "관광지": "att",
        "명소": "att",
        "음식점": "food",
        "맛집": "food",
        "박물관": "muse",
        "쇼핑": "shop",
    }
    normalized_category = category_map.get(category.lower().strip(), category.lower().strip())
    category_name = {
        "att": "관광지",
        "food": "음식점",
        "muse": "박물관",
        "shop": "쇼핑",
    }

    try:
        places = mock_api.fetch_places(found["code"], normalized_category)
    except (LookupError, ValueError) as error:
        return f"장소를 조회하지 못했습니다: {error}"

    lines = [f"{found['nm']} {category_name.get(normalized_category, category)} 후보"]
    for place in sorted(places, key=lambda item: item["rating_x10"], reverse=True):
        fee = "무료" if place["fee_minor"] == 0 else _format_krw(place["fee_minor"])
        lines.append(
            f"- {place['nm']} | 평점 {place['rating_x10'] / 10:.1f}/5 "
            f"({place['reviews']:,}개 리뷰) | "
            f"{place['open_h']:02d}:00~{place['close_h']:02d}:00 | 입장료 {fee}"
        )

    return "\n".join(lines)
