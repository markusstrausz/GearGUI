import tkinter as tk
from typing import Any

import gear


def _assert_nonempty(name: str, code: str) -> None:
    if not isinstance(code, str) or not code.strip():
        raise AssertionError(f"{name} returned empty SCAD code")


def run_scad_smoke_tests() -> None:
    cases: list[tuple[str, dict[str, Any], Any]] = [
        (
            "spur",
            {
                "modul": 1.0,
                "zahnzahl": 30,
                "breite": 10.0,
                "bohrung": 5.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 0.0,
                "optimiert": True,
                "paar": False,
                "profile_shift": 0.0,
            },
            gear.scad_spur_gear,
        ),
        (
            "herringbone",
            {
                "modul": 1.0,
                "zahnzahl": 30,
                "breite": 10.0,
                "bohrung": 5.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 35.0,
                "paar": False,
                "profile_shift": 0.0,
            },
            gear.scad_herringbone_gear,
        ),
        (
            "rack",
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
            gear.scad_rack,
        ),
        (
            "worm",
            {
                "modul": 1.0,
                "zahnzahl": 1,
                "breite": 30.0,
                "bohrung": 2.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 10.0,
                "zusammengebaut": True,
            },
            gear.scad_worm,
        ),
        (
            "worm_gear_pair",
            {
                "modul": 1.0,
                "zahnzahl": 30,
                "thread_starts": 2,
                "breite": 10.0,
                "laenge_schnecke": 20.0,
                "bohrung_schnecke": 4.0,
                "bohrung": 5.0,
                "eingriffswinkel": 20.0,
                "steigungswinkel": 10.0,
                "optimiert": True,
                "paar": True,
                "zusammengebaut": True,
            },
            gear.scad_worm_gear,
        ),
        (
            "ring_with_inner",
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
            gear.scad_ring_gear,
        ),
        (
            "planetary",
            {
                "modul": 1.0,
                "sonne_zähne": 16,
                "planet_zähne": 9,
                "anzahl_planeten": 3,
                "breite": 5.0,
                "randbreite": 3.0,
                "bohrung": 4.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 30.0,
                "zusammengebaut": True,
                "optimiert": True,
            },
            gear.scad_planetary_gear,
        ),
        (
            "bevel_single",
            {
                "modul": 1.0,
                "zahnzahl": 30,
                "teilkegelwinkel": 45.0,
                "zahnbreite": 8.0,
                "bohrung": 5.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 0.0,
                "animation_umkehren_einzel": False,
            },
            gear.scad_bevel_gear,
        ),
        (
            "bevel_pair",
            {
                "modul": 1.0,
                "zahnzahl": 30,
                "zahnzahl2": 11,
                "achswinkel": 90.0,
                "teilkegelwinkel": 45.0,
                "zahnbreite": 8.0,
                "bohrung": 5.0,
                "bohrung2": 4.0,
                "eingriffswinkel": 20.0,
                "schraegungswinkel": 0.0,
                "zusammengebaut": True,
                "paar": True,
                "animation_umkehren": False,
            },
            gear.scad_bevel_gear_pair,
        ),
    ]

    for name, params, func in cases:
        code = func(params, anim_angle=45)
        _assert_nonempty(name, code)


def run_app_start_smoke_test() -> None:
    original_check_paths = gear.check_paths
    try:
        # Verhindert Messageboxen im Smoke-Test bei fehlender OpenSCAD-Installation.
        gear.check_paths = lambda: True
        app = gear.GearGUI()
        app.update_idletasks()
        app.destroy()
    except tk.TclError:
        # Headless/CI-Umgebungen sollen den Smoke-Test nicht hart scheitern lassen.
        return
    finally:
        gear.check_paths = original_check_paths


def main() -> int:
    try:
        run_scad_smoke_tests()
        run_app_start_smoke_test()
    except Exception as exc:
        print(f"Smoke test failed: {exc}")
        return 1

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
