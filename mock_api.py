"""가짜 여행 API (mock). 수정하지 마세요.

실제 외부 서비스처럼 '가공되지 않은' 원본 응답을 돌려줍니다.
도시/공항 코드, unix timestamp, 최소 화폐 단위(minor unit), 10배 정수 온도가 그대로 나옵니다.
이걸 LLM이 읽기 좋은 형태로 바꾸는 것이 이번 과제입니다.

같은 인자로 부르면 항상 같은 값이 나옵니다 (난수도, 현재 시각도 쓰지 않습니다).
없는 도시/공항/카테고리를 넘기면 LookupError 가 납니다.

  python mock_api.py   # 자체 점검 (API 키 불필요)
"""

import hashlib
from datetime import datetime, timezone

CITIES = {
    "SEL": {"nm": "Seoul", "cc": "KR", "apt": "ICN"},
    "TYO": {"nm": "Tokyo", "cc": "JP", "apt": "HND"},
    "OSA": {"nm": "Osaka", "cc": "JP", "apt": "KIX"},
    "PAR": {"nm": "Paris", "cc": "FR", "apt": "CDG"},
    "ROM": {"nm": "Rome", "cc": "IT", "apt": "FCO"},
    "BCN": {"nm": "Barcelona", "cc": "ES", "apt": "BCN"},
    "NYC": {"nm": "New York", "cc": "US", "apt": "JFK"},
    "BKK": {"nm": "Bangkok", "cc": "TH", "apt": "BKK"},
}

_AIRPORTS = {v["apt"]: c for c, v in CITIES.items()}
_CARRIERS = ["KE", "OZ", "AF", "JL", "TG", "UA"]
_BRANDS = ["Grand", "Central", "Riverside", "Park", "Old Town", "Station"]
_PLACES = {
    "att": ["Old Quarter", "Hilltop Park", "Riverwalk", "Grand Cathedral"],
    "food": ["Market Hall", "Noodle Alley", "Rooftop Bistro", "Corner Bakery"],
    "muse": ["City Museum", "Modern Art Wing", "Maritime Museum", "History House"],
    "shop": ["Main Street Arcade", "Flea Market", "Design Mall", "Book Row"],
}
_WMO = [0, 1, 3, 45, 61, 63, 71, 80]


def _seed(*parts) -> int:
    key = "|".join(str(p) for p in parts).encode()
    return int(hashlib.md5(key).hexdigest()[:12], 16)


def _epoch(date: str, hour: int) -> int:
    d = datetime.strptime(date, "%Y-%m-%d").replace(hour=hour, tzinfo=timezone.utc)
    return int(d.timestamp())


def _city(code: str) -> dict:
    city = CITIES.get(str(code).upper())
    if city is None:
        raise LookupError(f"unknown city code: {code}")
    return city


def search_city(q: str) -> list:
    """도시 이름 일부 또는 코드로 도시를 찾는다. 못 찾으면 빈 리스트."""
    q = str(q).strip().lower()
    if not q:
        return []
    return [
        {"code": code, **city}
        for code, city in CITIES.items()
        if q in city["nm"].lower() or q == code.lower() or q == city["apt"].lower()
    ]


def fetch_flights(apt_from: str, apt_to: str, date: str) -> list:
    """공항 코드 두 개와 YYYY-MM-DD 날짜로 항공편 목록을 가져온다."""
    for apt in (apt_from, apt_to):
        if str(apt).upper() not in _AIRPORTS:
            raise LookupError(f"unknown airport: {apt}")
    src, dst = apt_from.upper(), apt_to.upper()
    s = _seed("flights", src, dst, date)
    out = []
    for i in range(3 + s % 3):
        r = s >> (i * 7)
        dep = _epoch(date, 6 + (r >> 3) % 15)
        out.append({
            "fno": f"{_CARRIERS[r % len(_CARRIERS)]}{100 + r % 800}",
            "dep_apt": src,
            "arr_apt": dst,
            "dep": dep,
            "arr": dep + 3600 * (2 + r % 12) + 600 * (r % 6),
            "cls": "E" if i % 3 else "B",
            "price_minor": 21000000 + (r % 90) * 1300000 + (0 if i % 3 else 240000000),
            "cur": "KRW",
            "stops": (r >> 5) % 2,
            "seats": 1 + r % 9,
        })
    return out


def fetch_hotels(city_code: str, checkin: str, checkout: str) -> list:
    """도시 코드와 체크인/체크아웃 날짜로 숙소 목록을 가져온다."""
    _city(city_code)
    nights = (datetime.strptime(checkout, "%Y-%m-%d") - datetime.strptime(checkin, "%Y-%m-%d")).days
    if nights <= 0:
        raise LookupError("checkout must be after checkin")
    s = _seed("hotels", city_code.upper(), checkin, checkout)
    out = []
    for i in range(4 + s % 3):
        r = s >> (i * 5)
        out.append({
            "hid": f"H{r % 100000:05d}",
            "nm": f"{_BRANDS[r % len(_BRANDS)]} Hotel {city_code.upper()}",
            "star": 2 + r % 4,
            "price_minor_night": 6000000 + (r % 40) * 900000,
            "cur": "KRW",
            "dist_m": 200 + (r % 60) * 130,
            "nights": nights,
            "avail": (r >> 4) % 5 != 0,
        })
    return out


def fetch_places(city_code: str, cat: str) -> list:
    """도시 코드와 카테고리(att/food/muse/shop)로 장소 목록을 가져온다."""
    _city(city_code)
    names = _PLACES.get(str(cat).lower())
    if names is None:
        raise LookupError(f"unknown category: {cat} (use one of {sorted(_PLACES)})")
    s = _seed("places", city_code.upper(), cat.lower())
    city = _city(city_code)
    out = []
    for i, name in enumerate(names):
        r = s >> (i * 6)
        out.append({
            "pid": f"P{r % 100000:05d}",
            "nm": f"{city['nm']} {name}",
            "cat": cat.lower(),
            "rating_x10": 30 + r % 20,
            "reviews": 40 + r % 4000,
            "open_h": 8 + r % 4,
            "close_h": 17 + r % 6,
            "fee_minor": 0 if r % 3 else 100000 + (r % 20) * 50000,
            "cur": "KRW",
        })
    return out


def fetch_weather(city_code: str, date: str) -> dict:
    """도시 코드와 YYYY-MM-DD 날짜로 일별 날씨를 가져온다."""
    _city(city_code)
    datetime.strptime(date, "%Y-%m-%d")
    r = _seed("weather", city_code.upper(), date)
    tmin = -50 + r % 260
    codes = _WMO if tmin < 20 else [c for c in _WMO if c != 71]  # 영상이면 눈은 빼고
    return {
        "wmo": codes[r % len(codes)],
        "tmin_cx10": tmin,
        "tmax_cx10": tmin + 30 + (r >> 3) % 90,
        "pop_pct": (r >> 6) % 101,
        "wind_ms_x10": (r >> 9) % 120,
    }


if __name__ == "__main__":
    assert fetch_weather("PAR", "2026-09-01") == fetch_weather("par", "2026-09-01"), "결정적이지 않음"
    assert search_city("par")[0]["code"] == "PAR"
    assert search_city("없는도시") == []
    assert all(f["dep"] < f["arr"] for f in fetch_flights("ICN", "CDG", "2026-09-01"))
    assert fetch_hotels("PAR", "2026-09-01", "2026-09-04")[0]["nights"] == 3
    assert len(fetch_places("PAR", "food")) == 4
    for bad in (lambda: fetch_weather("XXX", "2026-09-01"),
                lambda: fetch_flights("ICN", "XXX", "2026-09-01"),
                lambda: fetch_places("PAR", "nope")):
        try:
            bad()
            raise AssertionError("LookupError 가 나야 합니다")
        except LookupError:
            pass
    print("ok")
