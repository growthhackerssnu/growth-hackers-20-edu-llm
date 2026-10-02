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


def _valid_date(value: str, label: str = "날짜") -> str | None:
    """ISO 날짜를 검사하고 도구 응답용 오류 문구를 돌려준다."""
    try:
        if not isinstance(value, str) or len(value) != 10:
            raise ValueError
        datetime.strptime(value, "%Y-%m-%d")
    except (TypeError, ValueError):
        return f"{label} '{value}' 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해 주세요."
    return None


def _resolve_city(value: str) -> tuple[dict | None, str | None]:
    """도시명·도시 코드·공항 코드로 도시를 찾고 모호함을 보고한다."""
    hits = mock_api.search_city(value)
    if not hits:
        return None, f"'{value}' 도시를 찾지 못했습니다. 지원 도시: Seoul, Tokyo, Osaka, Paris, Rome, Barcelona, New York, Bangkok."
    if len(hits) > 1:
        names = ", ".join(f"{hit['nm']} ({hit['code']})" for hit in hits)
        return None, f"'{value}'에 해당하는 도시가 여러 곳입니다. 하나를 지정해 주세요: {names}."
    return hits[0], None


def _won(minor: int) -> str:
    """KRW 최소 단위를 원 단위 문자열로 바꾼다."""
    return f"{minor // 100:,}원" if minor % 100 == 0 else f"{minor / 100:,.2f}원"


def get_weather(city: str, date: str) -> str:
    """특정 도시의 특정 날짜 날씨를 조회한다.

    city는 도시 이름(예: Paris), 도시 코드(예: PAR), 공항 코드(예: CDG)
    중 하나이고 date는 YYYY-MM-DD 형식이어야 한다.
    """
    found, error = _resolve_city(city)
    if error:
        return error
    error = _valid_date(date)
    if error:
        return error
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
    있다. 시간은 UTC로 표시하고 최소 화폐 단위는 원으로 변환한다.
    """
    error = _valid_date(date, "출발 날짜")
    if error:
        return error
    src, error = _resolve_city(departure)
    if error:
        return f"출발지 {error}"
    dst, error = _resolve_city(arrival)
    if error:
        return f"도착지 {error}"
    if src["code"] == dst["code"]:
        return "출발지와 도착지는 서로 다른 도시여야 합니다."
    try:
        flights = mock_api.fetch_flights(src["apt"], dst["apt"], date)
    except (LookupError, ValueError) as exc:
        return f"항공편을 조회하지 못했습니다: {exc}"
    if not flights:
        return f"{date} {src['nm']} → {dst['nm']} 항공편이 없습니다."
    lines = [f"{date} {src['nm']} ({src['apt']}) → {dst['nm']} ({dst['apt']}) 항공편 후보 ({len(flights)}개):"]
    for flight in flights:
        dep = datetime.fromtimestamp(flight["dep"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        arr = datetime.fromtimestamp(flight["arr"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        stops = "직항" if flight["stops"] == 0 else f"경유 {flight['stops']}회"
        cabin = "비즈니스석" if flight["cls"] == "B" else "이코노미석"
        lines.append(
            f"- {flight['fno']} {dep} 출발 → {arr} 도착 (UTC, {stops}, {cabin}, "
            f"잔여 {flight['seats']}석, {_won(flight['price_minor'])})"
        )
    lines.append("※ 시간은 UTC 기준이며 실제 운항 정보가 아닌 과제용 모의 데이터입니다.")
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    mock_api.fetch_hotels의 1박 요금, 숙박 일수, 총액, 이용 가능 여부를
    사람이 읽기 좋은 문자열로 반환한다.
    """
    for label, value in (("체크인 날짜", checkin), ("체크아웃 날짜", checkout)):
        error = _valid_date(value, label)
        if error:
            return error
    try:
        in_date = datetime.strptime(checkin, "%Y-%m-%d").date()
        out_date = datetime.strptime(checkout, "%Y-%m-%d").date()
    except ValueError:
        return "체크인·체크아웃 날짜를 YYYY-MM-DD 형식으로 입력해 주세요."
    if out_date <= in_date:
        return "체크아웃 날짜는 체크인 날짜보다 뒤여야 합니다."
    found, error = _resolve_city(city)
    if error:
        return error
    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as exc:
        return f"숙소를 조회하지 못했습니다: {exc}"
    nights = (out_date - in_date).days
    if not hotels:
        return f"{found['nm']}에서 {checkin}~{checkout} 숙소 후보가 없습니다."
    lines = [f"{found['nm']} 숙소 후보, {checkin} 체크인 · {checkout} 체크아웃 ({nights}박):"]
    for hotel in hotels:
        avail = "예약 가능" if hotel["avail"] else "예약 불가"
        total = hotel["price_minor_night"] * nights
        lines.append(
            f"- {hotel['nm']} ({hotel['star']}성급, {avail}, 도심에서 {hotel['dist_m']:,}m): "
            f"1박 {_won(hotel['price_minor_night'])}, 총 {_won(total)}"
        )
    lines.append("※ 가격과 예약 가능 여부는 과제용 모의 데이터입니다.")
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    mock_api.fetch_places의 평점·리뷰 수·운영 시간·입장료를 사람이 읽기
    좋은 문자열로 반환한다.
    """
    found, error = _resolve_city(city)
    if error:
        return error
    cat = str(category).strip().lower()
    aliases = {"관광지": "att", "음식점": "food", "박물관": "muse", "쇼핑": "shop"}
    cat = aliases.get(cat, cat)
    if cat not in _CATEGORY_KO:
        return "장소 유형을 확인할 수 없습니다. 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중에서 골라 주세요."
    try:
        places = mock_api.fetch_places(found["code"], cat)
    except (LookupError, ValueError) as exc:
        return f"장소를 조회하지 못했습니다: {exc}"
    if not places:
        return f"{found['nm']}의 {_CATEGORY_KO[cat]} 후보가 없습니다."
    lines = [f"{found['nm']} {_CATEGORY_KO[cat]} 후보:"]
    for place in places:
        fee = "무료" if place["fee_minor"] == 0 else _won(place["fee_minor"])
        lines.append(
            f"- {place['nm']} (평점 {place['rating_x10'] / 10:.1f}/5, "
            f"리뷰 {place['reviews']:,}개, 운영 {place['open_h']:02d}:00~{place['close_h']:02d}:00, 입장료 {fee})"
        )
    lines.append("※ 평점·운영 시간·입장료는 과제용 모의 데이터입니다.")
    return "\n".join(lines)
