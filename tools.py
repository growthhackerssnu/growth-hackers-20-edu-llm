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

_CABIN_NAMES = {"E": "이코노미", "B": "비즈니스"}
_PLACE_CATEGORY_NAMES = {
    "att": "관광지",
    "food": "음식점",
    "muse": "박물관",
    "shop": "쇼핑",
}


def _resolve_city(query: str, label: str) -> dict:
    """도시명·도시 코드·공항 코드로 도시를 찾고, 실패 이유를 전달한다."""
    hits = mock_api.search_city(query)
    if not hits:
        raise ValueError(f"{label} '{query}'를 찾지 못했습니다.")
    return hits[0]


def _format_location(city: dict) -> str:
    """도시명과 도시·대표 공항 코드를 함께 표시한다."""
    return f"{city['nm']} ({city['code']} / {city['apt']})"


def _format_utc_time(timestamp: int) -> str:
    """Unix timestamp를 사람이 읽을 수 있는 UTC 시각으로 바꾼다."""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _format_duration(seconds: int) -> str:
    """초 단위 시간을 'N시간 N분' 형식으로 바꾼다."""
    hours, remainder = divmod(seconds, 3600)
    return f"{hours}시간 {remainder // 60}분"


def _format_money(amount_minor: int, currency: str) -> str:
    """최소 화폐 단위 금액을 사람이 읽기 쉬운 통화 표기로 바꾼다."""
    amount = amount_minor / 100
    if currency == "KRW":
        return f"₩{amount:,.0f}"
    return f"{currency} {amount:,.2f}"


def _format_distance(meters: int) -> str:
    """미터 단위 거리를 읽기 쉬운 거리 단위로 바꾼다."""
    if meters < 1000:
        return f"{meters}m"
    return f"{meters / 1000:.1f}km"


def _format_fee(amount_minor: int, currency: str) -> str:
    """입장료를 무료 또는 통화 표기로 바꾼다."""
    if amount_minor == 0:
        return "무료"
    return _format_money(amount_minor, currency)



def get_weather(city: str, date: str) -> str:
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
    """출발지·도착지·날짜의 항공편을 사람이 읽기 쉬운 형식으로 조회한다.

    ``departure``와 ``arrival``에는 도시명, 도시 코드, 또는 공항 코드를 쓸 수 있다.
    도시명과 코드(도시 코드 / 대표 공항 코드)를 함께 표시하며, 시각은 UTC이다.
    """
    try:
        source = _resolve_city(departure, "출발지")
        destination = _resolve_city(arrival, "도착지")
    except ValueError as error:
        return str(error)

    try:
        flights = mock_api.fetch_flights(source["apt"], destination["apt"], date)
    except (LookupError, ValueError) as error:
        return f"요청을 처리하지 못했습니다: {error}"

    lines = [f"{date} 항공편: {_format_location(source)} → {_format_location(destination)}"]
    for flight in flights:
        stop_text = "직항" if flight["stops"] == 0 else f"경유 {flight['stops']}회"
        price = flight["price_minor"] / 100
        lines.append(
            f"- {flight['fno']} | {_format_utc_time(flight['dep'])} → {_format_utc_time(flight['arr'])} "
            f"| {_format_duration(flight['arr'] - flight['dep'])} | "
            f"{_CABIN_NAMES.get(flight['cls'], flight['cls'])} | {stop_text} | "
            f"잔여 {flight['seats']}석 | {flight['cur']} {price:,.0f}"
        )
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    mock_api.fetch_hotels의 가격(원화 최소 단위), 숙박 일수, 이용 가능 여부를
    사람이 읽기 좋은 문자열로 변환하는 것이 이 도구의 TODO다.
    """
    try:
        found = _resolve_city(city, "도시")
    except ValueError as error:
        return str(error)

    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as error:
        return f"요청을 처리하지 못했습니다: {error}"

    nights = hotels[0]["nights"] if hotels else 0
    lines = [
        f"{_format_location(found)} 숙소: {checkin} ~ {checkout} ({nights}박)"
    ]
    for hotel in hotels:
        total_price = hotel["price_minor_night"] * hotel["nights"]
        availability = "예약 가능" if hotel["avail"] else "예약 불가"
        lines.append(
            f"- {hotel['nm']} | {hotel['star']}성 | 도심 {_format_distance(hotel['dist_m'])} "
            f"| 1박 {_format_money(hotel['price_minor_night'], hotel['cur'])} "
            f"| 총액 {_format_money(total_price, hotel['cur'])} | {availability}"
        )
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    mock_api.fetch_places의 평점·운영 시간·입장료를 사람이 읽기 좋은 문자열로
    변환하는 것이 이 도구의 TODO다.
    """
    try:
        found = _resolve_city(city, "도시")
    except ValueError as error:
        return str(error)

    category_code = category.strip().lower()
    try:
        places = mock_api.fetch_places(found["code"], category_code)
    except (LookupError, ValueError) as error:
        return f"요청을 처리하지 못했습니다: {error}"

    category_name = _PLACE_CATEGORY_NAMES.get(category_code, category_code)
    lines = [f"{found['nm']} ({found['code']}) {category_name} 추천"]
    for place in places:
        lines.append(
            f"- {place['nm']} | 평점 {place['rating_x10'] / 10:.1f} "
            f"({place['reviews']:,}개 리뷰) | {place['open_h']:02d}:00~{place['close_h']:02d}:00 "
            f"| 입장료 {_format_fee(place['fee_minor'], place['cur'])}"
        )
    return "\n".join(lines)
