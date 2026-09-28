from django.test import SimpleTestCase

from fuel_route_service.services import GenericRouteService


def station(id, position, price):
    return {"id": id, "position": position, "price": price}


class PickFuelStopsTest(SimpleTestCase):

    def test_trip_within_range_needs_no_stop(self):
        resp = GenericRouteService.pick_fuel_stops([station(1, 20, 3.0)], 450)
        self.assertTrue(resp.success)
        self.assertEqual(resp.data, [])

    def test_buys_only_what_next_leg_needs(self):
        resp = GenericRouteService.pick_fuel_stops([station(1, 400, 3.0)], 700)
        self.assertEqual([stop["id"] for stop in resp.data], [1])
        self.assertAlmostEqual(resp.data[0]["gallons"], 20)
        self.assertAlmostEqual(resp.data[0]["cost"], 60)

    def test_prefers_cheaper_station(self):
        stations = [station(1, 300, 4.0), station(2, 450, 2.5), station(3, 480, 3.9)]
        resp = GenericRouteService.pick_fuel_stops(stations, 900)
        self.assertEqual([stop["id"] for stop in resp.data], [2])
        self.assertAlmostEqual(resp.data[0]["gallons"], 40)

    def test_every_leg_within_range_and_no_fill_bigger_than_tank(self):
        stations = [station(i, i * 90, 3.0 + (i % 3) * 0.1) for i in range(1, 30)]
        resp = GenericRouteService.pick_fuel_stops(stations, 2700)
        positions = [0] + [stop["position"] for stop in resp.data] + [2700]
        self.assertTrue(all(b - a <= 500 for a, b in zip(positions, positions[1:])))
        self.assertTrue(all(stop["gallons"] <= 50 for stop in resp.data))
        self.assertAlmostEqual(sum(stop["gallons"] for stop in resp.data), 220)

    def test_gap_bigger_than_range_fails(self):
        resp = GenericRouteService.pick_fuel_stops([station(1, 100, 3.0), station(2, 700, 3.0)], 900)
        self.assertFalse(resp.success)
