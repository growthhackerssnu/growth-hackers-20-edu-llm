"""여행 정보 도구 스켈레톤.

Google ADK는 타입 힌트와 docstring이 있는 일반 Python 함수를 도구로
등록한다. 아래 get_weather를 예시로 삼아 나머지 도구를 완성한다.
"""

import mock_api
from datetime import datetime, timezone

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

_CATEGORY_ALIASES = {
    "관광지": "att", "명소": "att", "att": "att",
    "음식점": "food", "식당": "food", "food": "food",
    "박물관": "muse", "미술관": "muse", "muse": "muse",
    "쇼핑": "shop", "shop": "shop",
}


def _date(value: str) -> datetime:
    """YYYY-MM-DD 문자열을 검증한다."""
    parsed = datetime.strptime(value, "%Y-%m-%d")
    if parsed.strftime("%Y-%m-%d") != value:
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다")
    return parsed


def _city(value: str) -> dict | None:
    hits = mock_api.search_city(value)
    if not hits:
        return None
    # 코드/공항 코드/정확한 도시명 우선. 부분 일치가 여러 개면 첫 결과 대신 모호함을 알린다.
    q = value.strip().casefold()
    exact = [h for h in hits if q in (h["code"].casefold(), h["apt"].casefold(), h["nm"].casefold())]
    if exact:
        return exact[0]
    return hits[0] if len(hits) == 1 else {"ambiguous": hits}


def _city_error(value: str, city: dict | None) -> str | None:
    if city is None:
        return f"'{value}' 도시를 찾지 못했습니다. 도시 이름이나 공항 코드를 확인해 주세요."
    if "ambiguous" in city:
        names = ", ".join(item["nm"] for item in city["ambiguous"])
        return f"'{value}'에 해당하는 도시가 여러 곳입니다({names}). 도시를 구체적으로 지정해 주세요."
    return None


def _won(minor: int) -> str:
    return f"₩{minor // 100:,}" if minor % 100 == 0 else f"₩{minor / 100:,.2f}"


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
    try:
        _date(date)
        src, dst = _city(departure), _city(arrival)
        for value, resolved in ((departure, src), (arrival, dst)):
            error = _city_error(value, resolved)
            if error:
                return error
        if src["code"] == dst["code"]:
            return "출발지와 도착지가 같습니다. 서로 다른 도시를 지정해 주세요."
        flights = mock_api.fetch_flights(src["apt"], dst["apt"], date)
    except (LookupError, ValueError) as error:
        return f"항공편을 조회하지 못했습니다: {error}"
    if not flights:
        return f"{date} {src['nm']}→{dst['nm']} 항공편이 없습니다."
    lines = [f"{date} {src['nm']}({src['apt']}) → {dst['nm']}({dst['apt']}) 항공편 후보:"]
    for f in sorted(flights, key=lambda item: item["dep"]):
        dep = datetime.fromtimestamp(f["dep"], timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        arr = datetime.fromtimestamp(f["arr"], timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        cabin = {"E": "이코노미", "B": "비즈니스"}.get(f["cls"], f["cls"])
        stops = "직항" if f["stops"] == 0 else f"경유 {f['stops']}회"
        lines.append(f"- {f['fno']} · {dep} 출발 / {arr} 도착 · {cabin} · {stops} · 표시 요금 {_won(f['price_minor'])} · 잔여 {f['seats']}석")
    lines.append("※ 시간은 UTC입니다. 가격·좌석은 예시 데이터이며, 요금이 1인 기준인지 총액인지는 제공되지 않습니다.")
    return "\n".join(lines)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    mock_api.fetch_hotels의 가격(원화 최소 단위), 숙박 일수, 이용 가능 여부를
    사람이 읽기 좋은 문자열로 변환하는 것이 이 도구의 TODO다.
    """
    try:
        _date(checkin)
        _date(checkout)
        if _date(checkout) <= _date(checkin):
            return "체크아웃은 체크인보다 뒤 날짜여야 합니다."
        found = _city(city)
        error = _city_error(city, found)
        if error:
            return error
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as error:
        return f"숙소를 조회하지 못했습니다: {error}"
    nights = (_date(checkout) - _date(checkin)).days
    if not hotels:
        return f"{found['nm']} {checkin}~{checkout} 숙소 후보가 없습니다."
    lines = [f"{found['nm']} 숙소 후보 ({checkin} 체크인, {checkout} 체크아웃, {nights}박):"]
    for h in sorted(hotels, key=lambda item: (not item["avail"], item["price_minor_night"])):
        status = "예약 가능" if h["avail"] else "예약 불가"
        total = h["price_minor_night"] * h["nights"]
        lines.append(f"- {h['nm']} · {h['star']}성급 · 1박 {_won(h['price_minor_night'])} / 총 { _won(total)} · 도심 기준 {h['dist_m']:,}m · {status}")
    lines.append("※ 가격은 원화 기준 예시 데이터입니다.")
    return "\n".join(lines)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    mock_api.fetch_places의 평점·운영 시간·입장료를 사람이 읽기 좋은 문자열로
    변환하는 것이 이 도구의 TODO다.
    """
    found = _city(city)
    error = _city_error(city, found)
    if error:
        return error
    cat = _CATEGORY_ALIASES.get(category.strip().casefold())
    if cat is None:
        return "카테고리는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중에서 선택해 주세요."
    try:
        places = mock_api.fetch_places(found["code"], cat)
    except LookupError as error:
        return f"장소를 조회하지 못했습니다: {error}"
    if not places:
        return f"{found['nm']}에 해당 카테고리의 장소가 없습니다."
    lines = [f"{found['nm']} {category} 장소 후보:"]
    for p in sorted(places, key=lambda item: item["rating_x10"], reverse=True):
        fee = "무료" if p["fee_minor"] == 0 else _won(p["fee_minor"])
        fee_label = "입장료" if cat in ("att", "muse") else "도구 비용 필드"
        lines.append(f"- {p['nm']} · 평점 {p['rating_x10'] / 10:.1f}/5 ({p['reviews']:,}개 리뷰) · 운영 {p['open_h']:02d}:00~{p['close_h']:02d}:00 · {fee_label} {fee}")
    note = "음식점 메뉴 가격은 제공되지 않습니다." if cat == "food" else "쇼핑 상품 가격은 제공되지 않습니다." if cat == "shop" else ""
    lines.append(f"※ 운영 시간과 요금은 예시 데이터입니다. {note}".strip())
    return "\n".join(lines)
