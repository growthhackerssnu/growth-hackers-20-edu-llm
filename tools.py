"""여행 정보 도구 스켈레톤.

Google ADK는 타입 힌트와 docstring이 있는 일반 Python 함수를 도구로
등록한다. 아래 get_weather를 예시로 삼아 나머지 도구를 완성한다.
"""

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
    departure_hits = mock_api.search_city(departure)
    if not departure_hits:
        return f"'{departure}' 출발 도시 또는 공항을 찾지 못했습니다."
    arrival_hits = mock_api.search_city(arrival)
    if not arrival_hits:
        return f"'{arrival}' 도착 도시 또는 공항을 찾지 못했습니다."

    departure_city = departure_hits[0]
    arrival_city = arrival_hits[0]
    try:
        flights = mock_api.fetch_flights(
            departure_city["apt"], arrival_city["apt"], date
        )
    except (LookupError, ValueError) as error:
        return f"항공편을 조회하지 못했습니다: {error}"

    results = [f"{departure_city['nm']} → {arrival_city['nm']} 항공편 ({date})"]
    for flight in flights:
        departure_time = mock_api.datetime.fromtimestamp(
            flight["dep"], mock_api.timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC")
        arrival_time = mock_api.datetime.fromtimestamp(
            flight["arr"], mock_api.timezone.utc
        ).strftime("%Y-%m-%d %H:%M UTC")
        cabin = "비즈니스" if flight["cls"] == "B" else "이코노미"
        stops = "직항" if flight["stops"] == 0 else f"경유 {flight['stops']}회"
        price = flight["price_minor"] / 100
        results.append(
            f"- {flight['fno']} ({cabin}, {stops}), "
            f"출발 {departure_time} {flight['dep_apt']} → "
            f"도착 {arrival_time} {flight['arr_apt']}, "
            f"{price:,.0f} {flight['cur']}, 잔여 좌석 {flight['seats']}석"
        )
    return "\n".join(results)


def get_hotels(city: str, checkin: str, checkout: str) -> str:
    """도시와 체크인·체크아웃 날짜(YYYY-MM-DD)의 숙소 후보를 조회한다.

    mock_api.fetch_hotels의 가격(원화 최소 단위), 숙박 일수, 이용 가능 여부를
    사람이 읽기 좋은 문자열로 변환하는 것이 이 도구의 TODO다.
    """
    hits = mock_api.search_city(city)
    if not hits:
        return f"'{city}' 도시를 찾지 못했습니다."

    found = hits[0]
    try:
        hotels = mock_api.fetch_hotels(found["code"], checkin, checkout)
    except (LookupError, ValueError) as error:
        return f"숙소를 조회하지 못했습니다: {error}"

    results = [
        f"{found['nm']} 숙소 ({checkin} ~ {checkout}, "
        f"{hotels[0]['nights'] if hotels else 0}박)"
    ]
    for hotel in hotels:
        nightly_price = hotel["price_minor_night"] / 100
        total_price = nightly_price * hotel["nights"]
        availability = "예약 가능" if hotel["avail"] else "예약 불가"
        results.append(
            f"- {hotel['nm']} ({hotel['star']}성급), {availability}, "
            f"1박 {nightly_price:,.0f} {hotel['cur']} / "
            f"총 {total_price:,.0f} {hotel['cur']} ({hotel['nights']}박), "
            f"중심지에서 {hotel['dist_m']}m"
        )
    return "\n".join(results)


def get_places(city: str, category: str) -> str:
    """도시의 장소 후보를 조회한다.

    category는 관광지(att), 음식점(food), 박물관(muse), 쇼핑(shop) 중 하나다.
    mock_api.fetch_places의 평점·운영 시간·입장료를 사람이 읽기 좋은 문자열로
    변환하는 것이 이 도구의 TODO다.
    """
    hits = mock_api.search_city(city)
    if not hits:
        return f"'{city}' 도시를 찾지 못했습니다."

    found = hits[0]
    try:
        places = mock_api.fetch_places(found["code"], category)
    except (LookupError, ValueError) as error:
        return f"장소를 조회하지 못했습니다: {error}"

    results = [f"{found['nm']} 장소 ({category})"]
    for place in places:
        rating = place["rating_x10"] / 10
        if place["fee_minor"] == 0:
            fee = "무료"
        else:
            fee = f"입장료 {place['fee_minor'] / 100:,.0f} {place['cur']}"
        results.append(
            f"- {place['nm']}: 평점 {rating:.1f}/5 "
            f"({place['reviews']:,}개 리뷰), "
            f"운영 {place['open_h']:02d}:00~{place['close_h']:02d}:00, {fee}"
        )
    return "\n".join(results)
