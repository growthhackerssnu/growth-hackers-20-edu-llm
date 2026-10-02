"""API 호출 없이 실행하는 여행 조회 도구 회귀 테스트.

실행: uv run python -m unittest -v test_tools
"""

import unittest
from unittest.mock import patch

import mock_api
import tools


class TravelToolsTests(unittest.TestCase):
    def test_city_aliases_and_categories(self):
        for city in tools._CITY_ALIASES:
            self.assertIn('℃', tools.get_weather(city, '2026-10-10'))
            for category in tools._CATEGORIES:
                self.assertIn('평점', tools.get_places(city, category))
        self.assertEqual(tools._find_city('ICN')['code'], 'SEL')

    def test_invalid_requests(self):
        requests = [
            lambda: tools.get_weather('없는도시', '2026-10-10'),
            lambda: tools.get_weather('o', '2026-10-10'),
            lambda: tools.get_weather('서울', '2026-02-30'),
            lambda: tools.get_weather('서울', '2026-1-1'),
            lambda: tools.get_flights('서울', '서울', '2026-10-10'),
            lambda: tools.get_hotels('파리', '2026-10-13', '2026-10-10'),
            lambda: tools.get_hotels('파리', '2026-10-10', '2026-10-10'),
            lambda: tools.get_places('파리', '없는분류'),
        ]
        for request in requests:
            self.assertIn('요청을 처리하지 못했습니다', request())

    def test_local_departure_dates_all_routes(self):
        for source in mock_api.CITIES:
            for destination in mock_api.CITIES:
                if source == destination:
                    continue
                result = tools.get_flights(source, destination, '2026-10-10')
                if result == '조회된 항공편이 없습니다.':
                    continue
                self.assertIn('현지 출발일 2026-10-10', result)
                for line in result.splitlines()[1:]:
                    self.assertIn('| 출발 2026-10-10 ', line)

    def test_dst_dates(self):
        for date in ['2026-03-08', '2026-11-01']:
            result = tools.get_flights('NYC', 'SEL', date)
            self.assertIn(f'| 출발 {date} ', result)

    def test_hotel_totals_and_availability(self):
        result = tools.get_hotels('도쿄', '2026-10-10', '2026-10-13')
        for hotel in mock_api.fetch_hotels('TYO', '2026-10-10', '2026-10-13'):
            line = next(line for line in result.splitlines() if hotel['hid'] in line)
            self.assertIn(tools._money(hotel['price_minor_night'] * 3, 'KRW'), line)
            self.assertIn('예약 가능' if hotel['avail'] else '예약 불가', line)

    def test_money_and_places(self):
        self.assertEqual(tools._money(21000000, 'KRW'), '210,000원')
        self.assertEqual(tools._money(12345, 'USD'), '123.45 USD')
        result = tools.get_places('도쿄', 'muse')
        for place in mock_api.fetch_places('TYO', 'muse'):
            line = next(line for line in result.splitlines() if place['pid'] in line)
            self.assertIn(f"{place['rating_x10'] / 10:.1f}/5", line)
            self.assertIn('무료' if place['fee_minor'] == 0 else tools._money(place['fee_minor'], 'KRW'), line)

    def test_empty_responses(self):
        for function, api, args in [
            (tools.get_flights, 'fetch_flights', ('서울', '도쿄', '2026-10-10')),
            (tools.get_hotels, 'fetch_hotels', ('도쿄', '2026-10-10', '2026-10-13')),
            (tools.get_places, 'fetch_places', ('도쿄', 'food')),
        ]:
            with patch.object(mock_api, api, return_value=[]):
                self.assertIn('없습니다', function(*args))


if __name__ == '__main__':
    unittest.main()
