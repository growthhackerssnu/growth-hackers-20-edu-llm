"""Google ADK 여행 일정 에이전트가 사용하는 조회 도구."""

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

_CLASS_KO = {"E": "이코노미", "B": "비즈니스"}
_CATEGORY_ALIASES = {
    "att": "att",
    "attraction": "att",
    "관광지": "att",
    "food": "food",
    "restaurant": "food",
    "음식점": "food",
    "muse": "muse",
    "museum": "muse",
    "박물관": "muse",
    "shop": "shop",
    "shopping": "shop",
    "쇼핑": "shop",
}
_CATEGORY_KO = {
    "att": "관광지",
    "food": "음식점",
    "muse": "박물관",
    "shop": "쇼핑",
}


def _find_city(query: str) -> dict | None:
    """도시 이름·도시 코드·공항 코드 중 첫 번째 일치 항목을 반환한다."""
    hits = mock_api.search_city(query)
    return hits[0] if hits else None


def _format_money(amount_minor: int, currency: str) -> str:
    """API의 최소 화폐 단위를 일반 화폐 단위 문자열로 변환한다."""
    amount = amount_minor / 100
    if currency == "KRW":
        return f"{amount:,.0f}원"
    return f"{amount:,.2f} {currency}"


def _format_utc(timestamp: int) -> str:
    """Unix timestamp를 시간대가 명시된 날짜·시각으로 변환한다."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes = remainder // 60
    return f"{hours}시간 {minutes}분" if minutes else f"{hours}시간"


def _format_distance(meters: int) -> str:
    return f"{meters / 1000:.1f}km" if meters >= 1000 else f"{meters}m"


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
    있다. 결과에는 항공편명, 출도착 시각(UTC), 비행시간, 좌석 등급, 경유,
    가격, 잔여 좌석이 포함된다.
    """
    origin = _find_city(departure)
    if origin is None:
        return f"출발지 '{departure}'를 찾지 못했습니다."

    destination = _find_city(arrival)
    if destination is None:
        return f"도착지 '{arrival}'를 찾지 못했습니다."

    if origin["apt"] == destination["apt"]:
        return "출발지와 도착지가 같습니다. 서로 다른 도시를 입력해 주세요."

    try:
        flights = mock_api.fetch_flights(origin["apt"], destination["apt"], date)
    except (LookupError, ValueError) as error:
        return f"항공편 요청을 처리하지 못했습니다: {error}"

    if not flights:
        return f"{origin['nm']} → {destination['nm']} {date} 항공편이 없습니다."

    lines = [
        f"{origin['nm']}({origin['apt']}) → "
        f"{destination['nm']}({destination['apt']}) {date} 항공편"
    ]
    for flight in sorted(flights, key=lambda item: item["dep"]):
        stops = "직항" if flight["stops"] == 0 else f"{flight['stops']}회 경유"
        cabin = _CLASS_KO.get(flight["cls"], flight["cls"])
        duration = _format_duration(flight["arr"] - flight["dep"])
        price = _format_money(flight["price_minor"], flight["cur"])
        lines.append(
            f"- {flight['fno']} | {_format_utc(flight['dep'])} 출발 → "
            f"{_format_utc(flight['arr'])} 도착 | {duration} | {stops} | "
            f"{cabin} | {price} | 잔여 {flight['seats']}석"
        )
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    결과에는 등급, 중심지 거리, 1박 가격, 전체 숙박비, 예약 가능 여부가
    포함된다.
    """
    found = _find_city(city)
    if found is None:
        return f"'{city}' 도시를 찾지 못했습니다."

    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as error:
        return f"숙소 요청을 처리하지 못했습니다: {error}"

    if not hotels:
        return f"{found['nm']} {checkin}~{checkout} 숙소가 없습니다."

    nights = hotels[0]["nights"]
    lines = [f"{found['nm']} {checkin}~{checkout} ({nights}박) 숙소"]
    ordered = sorted(
        hotels,
        key=lambda item: (not item["avail"], item["price_minor_night"]),
    )
    for hotel in ordered:
        nightly = _format_money(hotel["price_minor_night"], hotel["cur"])
        total = _format_money(
            hotel["price_minor_night"] * hotel["nights"], hotel["cur"]
        )
        availability = "예약 가능" if hotel["avail"] else "예약 불가"
        lines.append(
            f"- {hotel['nm']} ({hotel['hid']}) | {hotel['star']}성급 | "
            f"중심지에서 {_format_distance(hotel['dist_m'])} | "
            f"1박 {nightly}, 총 {total} | {availability}"
        )
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    한국어 카테고리명도 사용할 수 있다. 결과에는 평점, 리뷰 수, 운영 시간,
    입장료가 포함된다.
    """
    found = _find_city(city)
    if found is None:
        return f"'{city}' 도시를 찾지 못했습니다."

    category_code = _CATEGORY_ALIASES.get(str(category).strip().lower())
    if category_code is None:
        return (
            f"지원하지 않는 카테고리 '{category}'입니다. "
            "att(관광지), food(음식점), muse(박물관), shop(쇼핑) 중에서 "
            "선택해 주세요."
        )

    try:
        places = mock_api.fetch_places(found["code"], category_code)
    except (LookupError, ValueError) as error:
        return f"장소 요청을 처리하지 못했습니다: {error}"

    if not places:
        return f"{found['nm']}의 {_CATEGORY_KO[category_code]} 정보가 없습니다."

    lines = [f"{found['nm']} {_CATEGORY_KO[category_code]} 후보"]
    ordered = sorted(
        places,
        key=lambda item: (item["rating_x10"], item["reviews"]),
        reverse=True,
    )
    for place in ordered:
        fee = (
            "무료"
            if place["fee_minor"] == 0
            else _format_money(place["fee_minor"], place["cur"])
        )
        lines.append(
            f"- {place['nm']} ({place['pid']}) | 평점 "
            f"{place['rating_x10'] / 10:.1f}/5.0 "
            f"(리뷰 {place['reviews']:,}개) | "
            f"운영 {place['open_h']:02d}:00~{place['close_h']:02d}:00 | "
            f"입장료 {fee}"
        )
    return "\n".join(lines)
