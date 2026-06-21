import unittest
import sys
import types


if "PIL" not in sys.modules:
    pil_module = types.ModuleType("PIL")
    pil_image_module = types.ModuleType("PIL.Image")
    pil_imagetk_module = types.ModuleType("PIL.ImageTk")
    pil_module.Image = pil_image_module
    pil_module.ImageTk = pil_imagetk_module
    sys.modules["PIL"] = pil_module
    sys.modules["PIL.Image"] = pil_image_module
    sys.modules["PIL.ImageTk"] = pil_imagetk_module

import gear


class RegressionTests(unittest.TestCase):
    def test_worm_uses_z_rotation_axis(self) -> None:
        code = gear.scad_worm(
            {
                "modul": 1.0,
                "zahnzahl": 2,
                "breite": 20.0,
                "bohrung": 2.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 10.0,
                "zusammengebaut": True,
            },
            anim_angle=45,
        )
        self.assertIn("rotate([0, 0, 45]) worm(", code)
        self.assertNotIn("rotate([45, 0, 0])", code)

    def test_rack_with_pinion_in_assembled_mode(self) -> None:
        code = gear.scad_rack(
            {
                "modul": 1.0,
                "laenge": 80.0,
                "hoehe": 10.0,
                "breite": 8.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 0.0,
                "passendes_zahnrad": True,
                "zusammengebaut_ritzel": True,
                "zahnzahl_ritzel": 20,
                "bohrung_ritzel": 5.0,
            },
            anim_angle=90,
        )
        self.assertIn("rack(1.0, 80.0, 10.0, 8.0, 20.0, -0.0);", code)
        self.assertIn("spur_gear(1.0, 20, 8.0, 5.0, 20.0, 0.0, true);", code)

    def test_ring_with_inner_gear(self) -> None:
        code = gear.scad_ring_gear(
            {
                "modul": 1.0,
                "zahnzahl": 48,
                "breite": 8.0,
                "randbreite": 4.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 0.0,
                "innenzahnrad": True,
                "zahnzahl_innen": 30,
                "bohrung_innen": 4.0,
                "zusammengebaut_innen": True,
            },
            anim_angle=12,
        )
        self.assertIn("ring_gear(1.0, 48, 8.0, 4.0, 20.0, 0.0);", code)
        self.assertIn("spur_gear(1.0, 30, 8.0, 4.0, 20.0, 0.0, true);", code)
        self.assertIn("translate([9.0, 0, 0])", code)


if __name__ == "__main__":
    unittest.main()
