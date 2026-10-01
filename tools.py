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

_CLASS_KO = {"E": "일반석", "B": "비즈니스석"}
_CATEGORY_KO = {
    "att": "관광지",
    "food": "음식점",
    "muse": "박물관",
    "shop": "쇼핑",
}


def _find_city(query: str) -> dict | None:
    """도시 이름/도시 코드/공항 코드를 mock API의 도시 정보로 바꾼다."""
    hits = mock_api.search_city(query)
    return hits[0] if hits else None


def _format_krw(minor_units: int) -> str:
    """mock API의 KRW 최소 화폐 단위(1/100원)를 원 단위로 표시한다."""
    return f"{minor_units // 100:,}원"


def _format_timestamp(epoch_seconds: int) -> str:
    """Unix timestamp를 시간대가 명시된 읽기 쉬운 UTC 시각으로 바꾼다."""
    return datetime.fromtimestamp(epoch_seconds, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )


def get_weather(city: str, date: str) -> str:
    """특정 도시의 특정 날짜 날씨를 조회한다.

    city는 도시 이름(예: Paris), 도시 코드(예: PAR), 공항 코드(예: CDG)
    중 하나이고 date는 YYYY-MM-DD 형식이어야 한다.
    """
    found = _find_city(city)
    if found is None:
        return f"'{city}' 도시를 찾지 못했습니다."

    try:
        weather = mock_api.fetch_weather(found["code"], date)
    except (LookupError, TypeError, ValueError) as error:
        return f"요청을 처리하지 못했습니다: {error}"
    return (
        f"{found['nm']} {date}: {_WMO_KO.get(weather['wmo'], '알 수 없음')}, "
        f"{weather['tmin_cx10'] / 10:.1f}~{weather['tmax_cx10'] / 10:.1f}℃, "
        f"강수확률 {weather['pop_pct']}%"
    )


def get_flights(departure: str, arrival: str, date: str) -> str:
    """출발지·도착지와 날짜(YYYY-MM-DD)의 항공편 후보를 조회한다.

    departure와 arrival에는 도시 이름(예: Seoul), 도시 코드(예: SEL), 공항
    코드(예: ICN)를 사용할 수 있다. 결과에는 편명, 출도착 UTC 시각, 좌석
    등급, 경유 횟수, 잔여 좌석, 1인 가격이 포함된다.
    """
    origin = _find_city(departure)
    if origin is None:
        return f"출발지 '{departure}' 도시를 찾지 못했습니다."

    destination = _find_city(arrival)
    if destination is None:
        return f"도착지 '{arrival}' 도시를 찾지 못했습니다."

    try:
        flights = mock_api.fetch_flights(origin["apt"], destination["apt"], date)
    except (LookupError, TypeError, ValueError) as error:
        return f"항공편 요청을 처리하지 못했습니다: {error}"

    if not flights:
        return (
            f"{origin['nm']}({origin['apt']}) → "
            f"{destination['nm']}({destination['apt']}) {date} 항공편이 없습니다."
        )

    lines = [
        f"{origin['nm']}({origin['apt']}) → "
        f"{destination['nm']}({destination['apt']}) {date} 항공편 후보"
    ]
    for flight in flights:
        stops = "직항" if flight["stops"] == 0 else f"{flight['stops']}회 경유"
        cabin = _CLASS_KO.get(flight["cls"], flight["cls"])
        lines.append(
            f"- {flight['fno']}: {_format_timestamp(flight['dep'])} 출발 → "
            f"{_format_timestamp(flight['arr'])} 도착 | {cabin} | {stops} | "
            f"1인 {_format_krw(flight['price_minor'])} | "
            f"잔여 {flight['seats']}석"
        )
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    city에는 도시 이름, 도시 코드 또는 공항 코드를 사용할 수 있다. 결과에는
    호텔 ID, 등급, 중심지 거리, 예약 가능 여부, 1박 가격과 전체 숙박 가격이
    포함된다.
    """
    found = _find_city(city)
    if found is None:
        return f"'{city}' 도시를 찾지 못했습니다."

    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, TypeError, ValueError) as error:
        return f"숙소 요청을 처리하지 못했습니다: {error}"

    if not hotels:
        return f"{found['nm']}의 {checkin}~{checkout} 숙소 후보가 없습니다."

    nights = hotels[0]["nights"]
    lines = [
        f"{found['nm']} 숙소 후보 ({checkin} 체크인, {checkout} 체크아웃, "
        f"{nights}박)"
    ]
    for hotel in hotels:
        price_per_night = hotel["price_minor_night"]
        availability = "예약 가능" if hotel["avail"] else "예약 불가"
        lines.append(
            f"- {hotel['nm']} ({hotel['hid']}): {hotel['star']}성급 | "
            f"중심지에서 {hotel['dist_m'] / 1000:.1f}km | {availability} | "
            f"1박 {_format_krw(price_per_night)}, "
            f"총 {_format_krw(price_per_night * hotel['nights'])}"
        )
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    결과에는 장소 ID, 평점과 리뷰 수, 운영 시간, 입장료가 포함된다.
    """
    found = _find_city(city)
    if found is None:
        return f"'{city}' 도시를 찾지 못했습니다."

    normalized_category = str(category).strip().lower()
    if normalized_category not in _CATEGORY_KO:
        return (
            f"지원하지 않는 카테고리 '{category}'입니다. "
            "att(관광지), food(음식점), muse(박물관), shop(쇼핑) 중 "
            "하나를 사용하세요."
        )

    try:
        places = mock_api.fetch_places(found["code"], normalized_category)
    except (LookupError, TypeError, ValueError) as error:
        return f"장소 요청을 처리하지 못했습니다: {error}"

    if not places:
        return (
            f"{found['nm']}의 {_CATEGORY_KO[normalized_category]} 후보가 없습니다."
        )

    lines = [f"{found['nm']} {_CATEGORY_KO[normalized_category]} 후보"]
    for place in places:
        fee = (
            "무료"
            if place["fee_minor"] == 0
            else _format_krw(place["fee_minor"])
        )
        lines.append(
            f"- {place['nm']} ({place['pid']}): "
            f"평점 {place['rating_x10'] / 10:.1f}/5.0 "
            f"(리뷰 {place['reviews']:,}개) | "
            f"운영 {place['open_h']:02d}:00~{place['close_h']:02d}:00 | "
            f"입장료 {fee}"
        )
    return "\n".join(lines)
