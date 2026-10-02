"""실습용 여행 API 응답을 읽기 쉬운 한국어로 변환하는 ADK 도구."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import mock_api

_CITY_ALIASES = {"서울": "SEL", "도쿄": "TYO", "동경": "TYO", "오사카": "OSA", "파리": "PAR", "로마": "ROM", "바르셀로나": "BCN", "뉴욕": "NYC", "방콕": "BKK"}
_CATEGORIES = {"관광지": "att", "음식점": "food", "식당": "food", "박물관": "muse", "쇼핑": "shop"}
_TIMEZONES = {"SEL": "Asia/Seoul", "TYO": "Asia/Tokyo", "OSA": "Asia/Tokyo", "PAR": "Europe/Paris", "ROM": "Europe/Rome", "BCN": "Europe/Madrid", "NYC": "America/New_York", "BKK": "Asia/Bangkok"}


def _find_city(query: str) -> dict:
    query = query.strip()
    hits = mock_api.search_city(_CITY_ALIASES.get(query, query))
    if not hits:
        raise LookupError(f"'{query}' 도시를 찾지 못했습니다. 지원 도시: 서울, 도쿄, 오사카, 파리, 로마, 바르셀로나, 뉴욕, 방콕")
    if len(hits) > 1:
        raise LookupError("도시를 더 정확히 입력해주세요: " + ", ".join(hit["nm"] for hit in hits))
    return hits[0]


def _date(value: str) -> datetime:
    parsed = datetime.strptime(value, "%Y-%m-%d")
    if parsed.strftime("%Y-%m-%d") != value:
        raise ValueError("날짜는 YYYY-MM-DD 형식으로 입력해주세요.")
    return parsed


def _money(minor: int, currency: str) -> str:
    # 이 과제의 mock API는 원화 금액도 100배 정수로 제공한다.
    return f"{minor / 100:,.0f}원" if currency == "KRW" else f"{minor / 100:,.2f} {currency}"


def _timestamp(epoch: int) -> str:
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _local_time(epoch: int, city_code: str) -> datetime:
    return datetime.fromtimestamp(epoch, ZoneInfo(_TIMEZONES[city_code]))

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
    try:
        found = _find_city(city)
        _date(date)
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
    있다. 한국어 도시명도 지원한다. date는 출발 도시의 현지 출발 날짜다.
    가격은 1인 편도이며 출발·도착 현지 시각과 UTC를 함께 반환한다.
    항공편 번호, 좌석 등급, 경유 횟수, 잔여 좌석과 소요 시간을 반환한다.
    """
    try:
        src, dst = _find_city(departure), _find_city(arrival)
        requested = _date(date)
        if src["code"] == dst["code"]:
            raise ValueError("출발지와 도착지는 달라야 합니다.")
        # UTC 날짜 경계를 넘는 편도 출발 도시의 현지 날짜로 정확히 필터링한다.
        candidates = []
        for offset in (-1, 0, 1):
            utc_date = (requested + timedelta(days=offset)).strftime("%Y-%m-%d")
            candidates.extend(mock_api.fetch_flights(src["apt"], dst["apt"], utc_date))
        flights = [row for row in candidates if _local_time(row["dep"], src["code"]).strftime("%Y-%m-%d") == date]
    except (LookupError, ValueError) as error:
        return f"요청을 처리하지 못했습니다: {error}"
    lines = [f"[실습용 모의 데이터] {src['nm']}({src['apt']}) → {dst['nm']}({dst['apt']}), 현지 출발일 {date}, 1인 편도. 출발·도착 시각은 각 도시 현지 시각이며 UTC도 병기합니다."]
    for flight in sorted(flights, key=lambda row: row["price_minor"]):
        minutes = (flight["arr"] - flight["dep"]) // 60
        cabin = {"E": "이코노미", "B": "비즈니스"}.get(flight["cls"], flight["cls"])
        stops = "직항" if flight["stops"] == 0 else f"{flight['stops']}회 경유"
        dep_local = _local_time(flight['dep'], src['code']).strftime('%Y-%m-%d %H:%M %Z')
        arr_local = _local_time(flight['arr'], dst['code']).strftime('%Y-%m-%d %H:%M %Z')
        lines.append(f"- {flight['fno']} | 출발 {dep_local} ({_timestamp(flight['dep'])}) → 도착 {arr_local} ({_timestamp(flight['arr'])}) | {minutes // 60}시간 {minutes % 60}분 | {cabin}, {stops}, 잔여 {flight['seats']}석 | {_money(flight['price_minor'], flight['cur'])}")
    return "\n".join(lines) if flights else "조회된 항공편이 없습니다."


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    체크아웃은 체크인보다 뒤여야 한다. 1박 가격, 숙박 총액, 등급,
    중심지 거리와 예약 가능 여부를 반환한다. 숙소 가격은 객실 1개 기준이다.
    """
    try:
        found = _find_city(city)
        if _date(checkout) <= _date(checkin):
            raise ValueError("체크아웃 날짜는 체크인 날짜보다 뒤여야 합니다.")
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as error:
        return f"요청을 처리하지 못했습니다: {error}"
    lines = [f"[실습용 모의 데이터] {found['nm']} 숙소: {checkin} 체크인 → {checkout} 체크아웃. 객실 1개 기준."]
    for hotel in sorted(hotels, key=lambda row: (not row["avail"], row["price_minor_night"])):
        status = "예약 가능" if hotel["avail"] else "예약 불가"
        lines.append(f"- {hotel['nm']} ({hotel['hid']}) | {hotel['star']}성급 | 중심지 {hotel['dist_m'] / 1000:.2f}km | 1박 {_money(hotel['price_minor_night'], hotel['cur'])}, {hotel['nights']}박 총 {_money(hotel['price_minor_night'] * hotel['nights'], hotel['cur'])} | {status}")
    return "\n".join(lines) if hotels else "조회된 숙소가 없습니다."


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    한국어 카테고리명도 지원한다. 평점은 5점 만점이며 운영 시간은
    도시 현지 시각이다. 입장료와 리뷰 수를 함께 반환한다.
    """
    try:
        found = _find_city(city)
        category = _CATEGORIES.get(category.strip(), category.strip().lower())
        places = mock_api.fetch_places(found["code"], category)
    except (LookupError, ValueError) as error:
        return f"요청을 처리하지 못했습니다: {error}"
    lines = [f"[실습용 모의 데이터] {found['nm']} {category} 장소. 운영 시간은 현지 시각, 입장료는 1인 기준."]
    for place in sorted(places, key=lambda row: (row["rating_x10"], row["reviews"]), reverse=True):
        fee = "무료" if place["fee_minor"] == 0 else _money(place["fee_minor"], place["cur"])
        lines.append(f"- {place['nm']} ({place['pid']}) | 평점 {place['rating_x10'] / 10:.1f}/5, 리뷰 {place['reviews']:,}개 | {place['open_h']:02d}:00~{place['close_h']:02d}:00 | 입장료 {fee}")
    return "\n".join(lines) if places else "조회된 장소가 없습니다."
