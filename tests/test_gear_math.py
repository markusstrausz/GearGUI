import math
import unittest

import gear_math


class GearMathTests(unittest.TestCase):
    def test_spur_axis_distance(self) -> None:
        self.assertAlmostEqual(gear_math.spur_pair_axis_distance(2.0, 20, 30), 50.0)
        self.assertAlmostEqual(gear_math.spur_pair_axis_distance(1.0, 16, 24, 0.25), 20.5)

    def test_herringbone_axis_distance(self) -> None:
        self.assertAlmostEqual(gear_math.herringbone_pair_axis_distance(1.5, 12, 18), 22.5)

    def test_rack_pinion_distance_and_motion(self) -> None:
        self.assertAlmostEqual(gear_math.rack_pinion_axis_distance(1.0, 20), 10.0)
        self.assertAlmostEqual(gear_math.rack_pinion_motion(1.0, 20, 180.0), math.pi * 10.0)

    def test_worm_distance_and_bore_limit(self) -> None:
        dist = gear_math.worm_axis_distance(1.0, 2, 10.0, 30)
        self.assertAlmostEqual(dist, 20.7587704831, places=9)
        self.assertGreater(gear_math.worm_root_diameter(1.0, 2, 10.0), 0.0)

    def test_worm_invalid_lead_angle(self) -> None:
        with self.assertRaises(ValueError):
            gear_math.worm_axis_distance(1.0, 2, 0.0, 30)
        with self.assertRaises(ValueError):
            gear_math.worm_root_diameter(1.0, 2, 0.0)

    def test_ring_inner_axis_distance(self) -> None:
        self.assertAlmostEqual(gear_math.ring_inner_axis_distance(1.0, 48, 30), 9.0)
        with self.assertRaises(ValueError):
            gear_math.ring_inner_axis_distance(1.0, 30, 30)
        with self.assertRaises(ValueError):
            gear_math.ring_inner_axis_distance(1.0, 30, 0)

    def test_planetary_helpers(self) -> None:
        self.assertEqual(gear_math.planetary_ring_teeth(16, 9), 34)
        self.assertAlmostEqual(gear_math.planetary_planet_center_distance(1.0, 16, 9), 12.5)


if __name__ == "__main__":
    unittest.main()
