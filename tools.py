"""Mock travel information tools for the Google ADK travel agent.

All prices in ``mock_api`` are encoded in minor units (100 units per KRW),
and flight timestamps are Unix timestamps. These helpers turn those raw
values into concise Korean text that is useful to the agent and traveler.
"""

from datetime import date as Date, datetime, timezone

import mock_api


_WMO_KO = {
    0: "맑음",
    1: "대체로 맑음",
    3: "흐림",
    45: "안개",
    61: "비",
    63: "많은 비",
    71: "눈",
    80: "소나기",
}

_CATEGORY_ALIASES = {
    "관광지": "att",
    "명소": "att",
    "음식점": "food",
    "식당": "food",
    "맛집": "food",
    "박물관": "muse",
    "미술관": "muse",
    "쇼핑": "shop",
    "쇼핑몰": "shop",
}
_CATEGORY_KO = {"att": "관광지", "food": "음식점", "muse": "박물관", "shop": "쇼핑"}


def _parse_date(value: str, label: str) -> Date:
    """Parse a strict YYYY-MM-DD date or raise a readable ValueError."""
    if not isinstance(value, str):
        raise ValueError(f"{label}는 YYYY-MM-DD 형식의 날짜여야 합니다.")
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m-%d").date()
    except ValueError as error:
        raise ValueError(f"{label} '{value}'의 날짜 형식이 올바르지 않습니다. YYYY-MM-DD로 입력해 주세요.") from error
    if parsed.isoformat() != value.strip():
        raise ValueError(f"{label} '{value}'의 날짜 형식이 올바르지 않습니다. YYYY-MM-DD로 입력해 주세요.")
    return parsed


def _find_city(query: str, label: str = "도시") -> dict:
    """Resolve a city name/code/airport code, rejecting missing or ambiguous names."""
    hits = mock_api.search_city(query)
    if not hits:
        raise LookupError(f"'{query}' {label}를 찾지 못했습니다. Seoul, Tokyo, Osaka, Paris, Rome, Barcelona, New York, Bangkok 중에서 입력해 주세요.")
    if len(hits) > 1:
        names = ", ".join(hit["nm"] for hit in hits)
        raise LookupError(f"'{query}'에 해당하는 {label}가 여러 개입니다({names}). 도시 이름이나 공항 코드를 더 정확히 입력해 주세요.")
    return hits[0]


def _format_money(minor: int, currency: str = "KRW") -> str:
    """Format mock API minor units; its KRW values use 100 units per won."""
    amount = int(minor)
    if currency.upper() == "KRW":
        return f"₩{amount / 100:,.0f}"
    return f"{amount / 100:,.2f} {currency.upper()}"


def _format_flight_time(timestamp: int) -> str:
    """Display the mock's UTC Unix timestamp as an unambiguous date and time."""
    return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def get_weather(city: str, date: str) -> str:
    """특정 도시의 특정 날짜 날씨를 조회한다.

    Args:
        city: 도시 이름(예: Paris), 도시 코드(예: PAR), 공항 코드(예: CDG).
        date: 조회 날짜(YYYY-MM-DD).
    """
    try:
        _parse_date(date, "날짜")
        found = _find_city(city)
        weather = mock_api.fetch_weather(found["code"], date.strip())
    except (LookupError, ValueError) as error:
        return f"날씨 조회 실패: {error}"
    return (
        f"{found['nm']} {date.strip()} 날씨(모의 데이터): {_WMO_KO.get(weather['wmo'], '알 수 없는 날씨')}, "
        f"최저 {weather['tmin_cx10'] / 10:.1f}℃ / 최고 {weather['tmax_cx10'] / 10:.1f}℃, "
        f"강수확률 {weather['pop_pct']}%, 풍속 {weather['wind_ms_x10'] / 10:.1f}m/s"
    )


def get_flights(departure: str, arrival: str, date: str) -> str:
    """출발지·도착지·날짜에 맞는 항공편 후보를 조회한다.

    Args:
        departure: 출발 도시 이름, 도시 코드 또는 공항 코드.
        arrival: 도착 도시 이름, 도시 코드 또는 공항 코드.
        date: 출발 날짜(YYYY-MM-DD).

    Returns:
        항공편 번호, 출발·도착 시각(UTC), 소요 시간, 경유, 좌석과 가격을
        사람이 읽기 쉬운 문자열로 반환한다. 결과는 예약이 아닌 모의 후보이다.
    """
    try:
        travel_date = _parse_date(date, "출발 날짜")
        src = _find_city(departure, "출발 도시")
        dst = _find_city(arrival, "도착 도시")
        if src["apt"] == dst["apt"]:
            return "항공편 조회 실패: 출발지와 도착지가 같습니다. 서로 다른 도시를 입력해 주세요."
        flights = mock_api.fetch_flights(src["apt"], dst["apt"], travel_date.isoformat())
    except (LookupError, ValueError) as error:
        return f"항공편 조회 실패: {error}"

    if not flights:
        return f"{src['nm']} → {dst['nm']} {travel_date.isoformat()}: 조회된 항공편이 없습니다."

    flights = sorted(flights, key=lambda flight: (flight["dep"], flight["price_minor"]))
    lines = [f"{src['nm']}({src['apt']}) → {dst['nm']}({dst['apt']}), {travel_date.isoformat()} 항공편 후보(모의 데이터):"]
    for flight in flights:
        duration_min = max(0, (flight["arr"] - flight["dep"]) // 60)
        duration = f"{duration_min // 60}시간 {duration_min % 60}분"
        cabin = {"E": "이코노미", "B": "비즈니스"}.get(flight["cls"], flight["cls"])
        stops = "직항" if flight["stops"] == 0 else f"{flight['stops']}회 경유"
        lines.append(
            f"- {flight['fno']} ({cabin}, {stops}, 남은 좌석 {flight['seats']}석): "
            f"출발 {_format_flight_time(flight['dep'])} → 도착 {_format_flight_time(flight['arr'])}, "
            f"소요 {duration}, {_format_money(flight['price_minor'], flight['cur'])}"
        )
    lines.append("※ 모의 데이터이며 실제 운항 시각·좌석·가격·예약 가능 여부가 아닙니다.")
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 숙박 기간에 맞는 숙소 후보를 조회한다.

    Args:
        city: 도시 이름, 도시 코드 또는 공항 코드.
        checkin: 체크인 날짜(YYYY-MM-DD).
        checkout: 체크아웃 날짜(YYYY-MM-DD). 체크인 이후 날짜여야 한다.

    Returns:
        1박 가격, 전체 숙박 가격, 거리, 별점과 예약 가능 여부가 포함된
        모의 숙소 후보 목록을 반환한다.
    """
    try:
        start = _parse_date(checkin, "체크인 날짜")
        end = _parse_date(checkout, "체크아웃 날짜")
        if end <= start:
            raise ValueError("체크아웃 날짜는 체크인 날짜보다 뒤여야 합니다.")
        found = _find_city(city)
        hotels = mock_api.fetch_hotels(found["code"], start.isoformat(), end.isoformat())
    except (LookupError, ValueError) as error:
        return f"숙소 조회 실패: {error}"

    hotels = sorted(hotels, key=lambda hotel: (not hotel["avail"], hotel["price_minor_night"]))
    nights = (end - start).days
    lines = [f"{found['nm']} {start.isoformat()}~{end.isoformat()} ({nights}박) 숙소 후보(모의 데이터):"]
    for hotel in hotels:
        total = hotel["price_minor_night"] * hotel["nights"]
        availability = "예약 가능" if hotel["avail"] else "예약 불가"
        lines.append(
            f"- {hotel['nm']} ({hotel['star']}성급, {availability}): "
            f"1박 {_format_money(hotel['price_minor_night'], hotel['cur'])}, "
            f"총 {_format_money(total, hotel['cur'])} / {nights}박, "
            f"중심지 기준 약 {hotel['dist_m']:,}m"
        )
    lines.append("※ 모의 데이터이며 실제 숙박 요금·예약 가능 여부가 아닙니다.")
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 관광지·음식점·박물관·쇼핑 장소 후보를 조회한다.

    Args:
        city: 도시 이름, 도시 코드 또는 공항 코드.
        category: att(관광지), food(음식점), muse(박물관), shop(쇼핑) 중 하나.
            한국어 별칭인 관광지, 음식점/식당, 박물관/미술관, 쇼핑도 가능하다.

    Returns:
        장소 이름, 평점, 리뷰 수, 운영 시간과 입장료를 포함한 모의 장소 목록.
    """
    raw_category = str(category).strip().lower()
    normalized_category = _CATEGORY_ALIASES.get(raw_category, raw_category)
    if normalized_category not in _CATEGORY_KO:
        return "장소 조회 실패: category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나여야 합니다."
    try:
        found = _find_city(city)
        places = mock_api.fetch_places(found["code"], normalized_category)
    except (LookupError, ValueError) as error:
        return f"장소 조회 실패: {error}"

    places = sorted(places, key=lambda place: (-place["rating_x10"], -place["reviews"]))
    lines = [f"{found['nm']} {_CATEGORY_KO[normalized_category]} 후보(모의 데이터):"]
    for place in places:
        fee = "무료" if place["fee_minor"] == 0 else _format_money(place["fee_minor"], place["cur"])
        lines.append(
            f"- {place['nm']}: 평점 {place['rating_x10'] / 10:.1f}/5 "
            f"(리뷰 {place['reviews']:,}개), 운영 {place['open_h']:02d}:00~{place['close_h']:02d}:00, "
            f"입장료 {fee}"
        )
    lines.append("※ 모의 데이터이며 실제 평점·운영 시간·입장료와 다를 수 있습니다.")
    return "\n".join(lines)
