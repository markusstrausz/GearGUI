import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import subprocess
import os
import sys
import shutil
import configparser
import threading
import math
from typing import Any, Callable

from gear_math import (
    herringbone_pair_axis_distance,
    planetary_planet_center_distance,
    planetary_ring_teeth,
    rack_pinion_axis_distance,
    rack_pinion_motion,
    ring_inner_axis_distance,
    spur_pair_axis_distance,
    worm_axis_distance,
    worm_root_diameter,
)

def resource_path(relative_path: str) -> str:
    """ Hilfsfunktion um Pfade für PyInstaller (EXE) und Entwicklungsumgebung zu finden. """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# >>> HIER ANPASSEN <<<
def get_config_path() -> str:
    if getattr(sys, 'frozen', False):
        # Wenn als EXE ausgeführt: Pfad direkt neben der .exe Datei
        base_path = os.path.dirname(sys.executable)
    else:
        # Wenn als Skript ausgeführt: Pfad im Skript-Ordner
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, "config.ini")

CONFIG_FILE = get_config_path()


class LocalizationManager:
    def __init__(self, lang_file, default_lang='de'):
        self.config = configparser.ConfigParser()
        self.lang_file = lang_file
        self.translations = {}
        self.current_lang = default_lang
        self.load_languages()
        self.load_last_language() # Load last used language
        self.subscribers = []

    def load_last_language(self):
        config = configparser.ConfigParser()
        if os.path.exists(CONFIG_FILE):
            config.read(CONFIG_FILE)
            if "Settings" in config and "last_language" in config["Settings"]:
                last_lang = config["Settings"]["last_language"]
                if last_lang in self.translations:
                    self.current_lang = last_lang

    def load_languages(self):
        if os.path.exists(self.lang_file):
            # Ensure config is cleared before reading to avoid duplicates if called multiple times
            # and to handle changes in lang.ini correctly.
            self.config = configparser.ConfigParser()
            self.config.read(self.lang_file, encoding='utf-8')
            for section in self.config.sections():
                # Normalize all keys to lowercase so lookups work reliably
                # even when the code uses different capitalization.
                self.translations[section] = {k.lower(): v for k, v in self.config.items(section)}
        else:
            print(f"WARNING: Language file not found at {self.lang_file}")

    def get_string(self, key, lang=None, **kwargs):
        lang_to_use = lang if lang else self.current_lang
        normalized_key = key.lower()
        return self.translations.get(lang_to_use, {}).get(normalized_key, f"KEY_NOT_FOUND:{key}").format(**kwargs)

    def set_language(self, lang_code):
        if lang_code in self.translations:
            # Save the preference to config.ini
            config = configparser.ConfigParser()
            if os.path.exists(CONFIG_FILE):
                config.read(CONFIG_FILE)
            if "Settings" not in config:
                config["Settings"] = {}
            config["Settings"]["last_language"] = lang_code
            with open(CONFIG_FILE, "w") as f:
                config.write(f)
            self.current_lang = lang_code
            for callback in self.subscribers:
                callback()

def get_openscad_path() -> str:
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if "Paths" in config and "openscad" in config["Paths"]:
            path = config["Paths"]["openscad"]
            if os.path.isfile(path):
                return path

    # Suche nach OpenSCAD in Standardpfaden und PATH
    candidates = [
        shutil.which("openscad"),
        shutil.which("openscad-nightly"),
        r"C:\Program Files\OpenSCAD\openscad.exe",
        r"C:\Program Files (x86)\OpenSCAD\openscad.exe",
        r"C:\Program Files\OpenSCAD-Nightly\openscad.exe",
    ]

    for p in candidates:
        if p and os.path.isfile(p):
            if "Paths" not in config: config["Paths"] = {}
            config["Paths"]["openscad"] = p
            with open(CONFIG_FILE, "w") as f:
                config.write(f)
            return p
    return ""

def get_gears_scad_path() -> str:
    config = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        config.read(CONFIG_FILE)
        if "Paths" in config and "gears_scad" in config["Paths"]:
            path = config["Paths"]["gears_scad"]
            if os.path.isfile(path):
                return path

    # Suche nach gears.scad relativ zum Skript oder im Unterordner
    base_dir = resource_path("")
    candidates = [
        os.path.join(base_dir, "gears-master", "gears.scad"),
        os.path.join(base_dir, "gears.scad"),
    ]

    for p in candidates:
        if os.path.isfile(p):
            if "Paths" not in config: config["Paths"] = {}
            config["Paths"]["gears_scad"] = p
            with open(CONFIG_FILE, "w") as f:
                config.write(f)
            return p
    return r"C:\Users\marku\OneDrive\Dokumente\python\Zahnrad3\gears-master\gears.scad"

OPENSCAD_EXE = get_openscad_path()
GEARS_SCAD_PATH = get_gears_scad_path() # This will be initialized later in GearGUI

# Global variable for LocalizationManager instance, initialized later
l10n_manager_global = None

def check_paths() -> bool: # Removed l10n_manager parameter, now uses global
    global l10n_manager_global
    print(f"Checking paths...")
    if not os.path.isfile(GEARS_SCAD_PATH):
        print(f"ERROR: gears.scad not found at {GEARS_SCAD_PATH}")
        messagebox.showerror(l10n_manager_global.get_string("error_title"),
            l10n_manager_global.get_string("error_gears_scad_not_found", path=GEARS_SCAD_PATH)
        )
        return False
    else:
        print(f"gears.scad found at {GEARS_SCAD_PATH}")
    if not os.path.isfile(OPENSCAD_EXE):
        print(f"WARNING: OpenSCAD executable not found at {OPENSCAD_EXE}")
        messagebox.showwarning(l10n_manager_global.get_string("warning_title"),
            l10n_manager_global.get_string("warning_openscad_not_found", path=OPENSCAD_EXE)
        )
    else:
        print(f"OpenSCAD executable found at {OPENSCAD_EXE}")
    return True


def open_in_openscad(path: str) -> None: # Removed l10n_manager parameter, now uses global
    if not os.path.isfile(OPENSCAD_EXE):
        return
    try:
        subprocess.Popen([OPENSCAD_EXE, path], shell=True) # Use shell=True for better compatibility
    except Exception as e:
        messagebox.showerror(l10n_manager_global.get_string("error_openscad_start"), str(e))


def export_with_openscad(scad_code: str, output_path: str) -> None:
    """Export non-SCAD formats by invoking OpenSCAD CLI with a temp SCAD file."""
    if not os.path.isfile(OPENSCAD_EXE):
        raise FileNotFoundError(l10n_manager_global.get_string("warning_openscad_not_found", path=OPENSCAD_EXE))

    temp_scad = os.path.join(os.path.dirname(__file__), "temp_export.scad")
    with open(temp_scad, "w", encoding="utf-8") as f:
        f.write(scad_code)

    try:
        result = subprocess.run(
            [OPENSCAD_EXE, "-o", output_path, temp_scad],
            check=False,
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            stderr_msg = (result.stderr or "").strip()
            raise RuntimeError(stderr_msg or l10n_manager_global.get_string("error_openscad_start"))
    finally:
        try:
            if os.path.exists(temp_scad):
                os.remove(temp_scad)
        except OSError:
            pass


def as_2d_projection_scad(scad_code: str) -> str:
    """Wrap model body in a 2D projection for curve-based exports like DXF."""
    lines = scad_code.splitlines()
    header = [l for l in lines if l.strip().startswith(("use <", "include <"))]
    body = [l for l in lines if not l.strip().startswith(("use <", "include <"))]
    return "\n".join(header) + "\nprojection(cut=true) {\n" + "\n".join(body) + "\n}\n"


def _parse_dxf_entities_to_segments(dxf_text: str) -> list[list[tuple[float, float]]]:
    """Extract simple 2D point segments from ASCII DXF entities.

    Supported entities: LINE, LWPOLYLINE, POLYLINE/VERTEX.
    """
    raw = [ln.rstrip("\r\n") for ln in dxf_text.splitlines()]
    pairs: list[tuple[str, str]] = []
    i = 0
    while i + 1 < len(raw):
        pairs.append((raw[i].strip(), raw[i + 1].strip()))
        i += 2

    segments: list[list[tuple[float, float]]] = []
    idx = 0
    while idx < len(pairs):
        code, val = pairs[idx]
        if code != "0":
            idx += 1
            continue

        if val == "LINE":
            x1 = y1 = x2 = y2 = None
            idx += 1
            while idx < len(pairs) and pairs[idx][0] != "0":
                c, v = pairs[idx]
                if c == "10":
                    x1 = float(v)
                elif c == "20":
                    y1 = float(v)
                elif c == "11":
                    x2 = float(v)
                elif c == "21":
                    y2 = float(v)
                idx += 1
            if None not in (x1, y1, x2, y2):
                segments.append([(x1, y1), (x2, y2)])
            continue

        if val == "LWPOLYLINE":
            pts: list[tuple[float, float]] = []
            closed = False
            x_curr = None
            idx += 1
            while idx < len(pairs) and pairs[idx][0] != "0":
                c, v = pairs[idx]
                if c == "70":
                    try:
                        closed = (int(v) & 1) == 1
                    except ValueError:
                        closed = False
                elif c == "10":
                    x_curr = float(v)
                elif c == "20" and x_curr is not None:
                    pts.append((x_curr, float(v)))
                    x_curr = None
                idx += 1
            if len(pts) >= 2:
                if closed and pts[0] != pts[-1]:
                    pts.append(pts[0])
                segments.append(pts)
            continue

        if val == "POLYLINE":
            idx += 1
            pts: list[tuple[float, float]] = []
            while idx < len(pairs):
                c0, v0 = pairs[idx]
                if c0 != "0":
                    idx += 1
                    continue
                if v0 == "SEQEND":
                    idx += 1
                    break
                if v0 != "VERTEX":
                    break
                idx += 1
                vx = vy = None
                while idx < len(pairs) and pairs[idx][0] != "0":
                    c, v = pairs[idx]
                    if c == "10":
                        vx = float(v)
                    elif c == "20":
                        vy = float(v)
                    idx += 1
                if None not in (vx, vy):
                    pts.append((vx, vy))
            if len(pts) >= 2:
                segments.append(pts)
            continue

        idx += 1

    return segments


def export_points_curve_txt(scad_code: str, output_path: str) -> None:
    """Export projected 2D geometry as point-curve TXT.

    Output format is intentionally plain for CAD importers:
    one point per line as "x;y".
    """
    temp_dxf = os.path.join(os.path.dirname(__file__), "temp_export_points.dxf")
    try:
        export_with_openscad(as_2d_projection_scad(scad_code), temp_dxf)
        with open(temp_dxf, "r", encoding="utf-8", errors="ignore") as f:
            dxf_text = f.read()
        segments = _parse_dxf_entities_to_segments(dxf_text)
        if not segments:
            raise RuntimeError("Keine auswertbaren Kurvenpunkte im DXF gefunden.")

        # For best compatibility pick the longest continuous curve first.
        main_seg = max(segments, key=len)

        with open(output_path, "w", encoding="utf-8") as out:
            for x, y in main_seg:
                out.write(f"{x:.6f};{y:.6f}\n")
    finally:
        try:
            if os.path.exists(temp_dxf):
                os.remove(temp_dxf)
        except OSError:
            pass


def generate_header() -> str:
    return f"use <{GEARS_SCAD_PATH.replace('\\', '/')}>;\n\n"


GEAR_CLEARANCE = 0.05


def meshing_phase_for_even(teeth: int) -> float:
    """Half-tooth phase with library clearance, only needed for even tooth counts."""
    return (180.0 * (1.0 - GEAR_CLEARANCE) / teeth) if teeth % 2 == 0 else 0.0


def format_ratio_text(output_value: int, input_value: int) -> str:
    """Returns a localized ratio text with decimal value and reduced fraction."""
    if output_value <= 0 or input_value <= 0:
        return l10n_manager_global.get_string("error_invalid_input")
    ratio = output_value / input_value
    divisor = math.gcd(output_value, input_value)
    out_reduced = output_value // divisor
    in_reduced = input_value // divisor
    if in_reduced == 1:
        return l10n_manager_global.get_string(
            "gear_ratio_integer",
            out=out_reduced,
        )
    return l10n_manager_global.get_string(
        "gear_ratio",
        ratio=ratio,
        out=out_reduced,
        inp=in_reduced,
    )


# ---------- SCAD-Generatoren ----------

def scad_spur_gear(params: dict[str, Any], anim_angle: float = 0) -> str:
    # spur_gear(modul, zahnzahl, breite, bohrung, eingriffswinkel=20, schraegungswinkel=0);
    m = params["modul"]
    z = params["zahnzahl"]
    b = params["breite"]
    d = params["bohrung"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    opt = "true" if params["optimiert"] else "false"
    ps = params.get("profile_shift", 0)
    
    display_mode = params.get("paar", "both")
    # Normalisierung für Rückwärts-Kompatibilität
    if isinstance(display_mode, bool):
        display_mode = "both" if display_mode else "gear1"
    
    code = generate_header()
    
    # Erste Zahnrad nur zeigen, wenn nicht "gear2"
    if display_mode != "gear2":
        code += f"rotate([0, 0, {anim_angle}]) spur_gear({m}, {z}, {b}, {d}, {pa}, {ha}, {opt}, {ps});\n"
    
    # Zweite Zahnrad nur zeigen, wenn "both" oder "gear2"
    if display_mode in ("both", "gear2"):
        z2 = params["zahnzahl2"]
        phase = meshing_phase_for_even(z2)
        # Übersetzung: Winkel_2 = -Winkel_1 * (Z1 / Z2) (negativ, da entgegengesetzte Drehrichtung)
        rot2 = phase - (anim_angle * (z / z2))
        if params.get("zusammengebaut"):
            dist = m * (z + z2) / 2 + (2 * ps * m)
            code += f"// Achsabstand: {dist}\n"
            code += f"translate([{dist}, 0, 0]) rotate([0, 0, {rot2}]) spur_gear({m}, {z2}, {b}, {d}, {pa}, -{ha}, {opt}, {ps});\n"
        else:
            # Nebeneinander platzieren mit 5mm Abstand
            sep = (m * z / 2) + (m * z2 / 2) + 5
            code += f"translate([{sep}, 0, 0]) rotate([0, 0, {rot2}]) spur_gear({m}, {z2}, {b}, {d}, {pa}, -{ha}, {opt}, {ps});\n"
    
    return code


def scad_herringbone_gear(params: dict[str, Any], anim_angle: float = 0) -> str:
    # herringbone_gear(modul, zahnzahl, breite, bohrung, eingriffswinkel=20, schraegungswinkel=45);
    m = params["modul"]
    z = params["zahnzahl"]
    b = params["breite"]
    d = params["bohrung"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    ps = params.get("profile_shift", 0)
    
    display_mode = params.get("paar", "both")
    # Normalisierung für Rückwärts-Kompatibilität
    if isinstance(display_mode, bool):
        display_mode = "both" if display_mode else "gear1"
    
    code = generate_header()
    
    # Erste Zahnrad nur zeigen, wenn nicht "gear2"
    if display_mode != "gear2":
        code += f"rotate([0, 0, {anim_angle}]) herringbone_gear({m}, {z}, {b}, {d}, {pa}, {ha}, true, {ps});\n"
    
    # Zweite Zahnrad nur zeigen, wenn "both" oder "gear2"
    if display_mode in ("both", "gear2"):
        z2 = params["zahnzahl2"]
        phase = meshing_phase_for_even(z2)
        rot2 = phase - (anim_angle * (z / z2)) # Übersetzung
        if params.get("zusammengebaut"):
            dist = m * (z + z2) / 2 + (2 * ps * m)
            code += f"// Achsabstand: {dist}\n"
            code += f"translate([{dist}, 0, 0]) rotate([0, 0, {rot2}]) herringbone_gear({m}, {z2}, {b}, {d}, {pa}, {ha}, true, {ps});\n"
        else:
            sep = (m * z / 2) + (m * z2 / 2) + 5
            code += f"translate([{sep}, 0, 0]) rotate([0, 0, {rot2}]) herringbone_gear({m}, {z2}, {b}, {d}, {pa}, {ha}, true, {ps});\n"
    return code


def scad_rack(params: dict[str, Any], anim_angle: float = 0) -> str:
    # rack(modul, length, height, width, pressure_angle=20, helix_angle=0);
    m = params["modul"]
    L = params["laenge"]
    H = params["hoehe"]
    W = params["breite"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    show_pinion = params.get("passendes_zahnrad", False)

    # Verschiebung der Zahnstange: Weg = r * alpha.
    # Ohne passendes Ritzel nutzen wir weiterhin die bisherige Referenz mit z=20.
    if show_pinion:
        z_pinion = params["zahnzahl_ritzel"]
        bore_pinion = params["bohrung_ritzel"]
        assembled = params.get("zusammengebaut_ritzel", True)
        pinion_phase = 360 / z_pinion

        if assembled:
            shift = rack_pinion_motion(m, z_pinion, anim_angle)
            # Wie in rack_and_pinion(): Mittelpunktabstand = m*z/2
            pinion_y = rack_pinion_axis_distance(m, z_pinion)
            return (
                generate_header()
                + f"translate([{-shift % (math.pi * m)}, 0, 0]) rack({m}, {L}, {H}, {W}, {pa}, -{ha});\n"
                + f"translate([0, {pinion_y}, 0]) rotate([0, 0, {pinion_phase - anim_angle}]) spur_gear({m}, {z_pinion}, {W}, {bore_pinion}, {pa}, {ha}, true);\n"
            )

        # Getrennte Darstellung (nicht zusammengebaut): Bauteile nebeneinander.
        sep_x = (L / 2) + rack_pinion_axis_distance(m, z_pinion) + 5
        pinion_y = m * z_pinion
        return (
            generate_header()
            + f"rack({m}, {L}, {H}, {W}, {pa}, -{ha});\n"
            + f"translate([{sep_x}, {pinion_y}, 0]) rotate([0, 0, {pinion_phase - anim_angle}]) spur_gear({m}, {z_pinion}, {W}, {bore_pinion}, {pa}, {ha}, true);\n"
        )

    shift = rack_pinion_motion(m, 20, anim_angle)
    return (
        generate_header()
        + f"translate([{-shift % (math.pi * m)}, 0, 0]) rack({m}, {L}, {H}, {W}, {pa}, {ha});\n"
    )


def scad_worm(params: dict[str, Any], anim_angle: float = 0) -> str:
    # worm(modul, thread_starts, length, bore, pressure_angle=20, lead_angle, together_built=true)
    m = params["modul"]
    ts = params["zahnzahl"]
    l = params["breite"]
    d = params["bohrung"]
    pa = params["eingriffswinkel"]
    la = params["schraegungswinkel"]
    tb = "true" if params.get("zusammengebaut", True) else "false"

    # Verhindere Division durch Null in OpenSCAD
    if la == 0:
        return f"// {l10n_manager_global.get_string('worm_lead_angle_required')}\n"

    return (
 generate_header()
        + f"rotate([0, 0, {anim_angle}]) worm({m}, {ts}, {l}, {d}, {pa}, {la}, {tb});\n" # Worm rotates around its own axis (Z-axis)
    )


def scad_worm_gear(params: dict[str, Any], anim_angle: float = 0) -> str:
    # worm_gear(modul, tooth_number, thread_starts, width, length, worm_bore, gear_bore, pressure_angle=20, lead_angle=10, optimized=true, together_built=true, show_spur=1, show_worm=1)
    m = params["modul"]
    z = params["zahnzahl"]
    ts = params["thread_starts"]
    w = params["breite"]
    l = params["laenge_schnecke"]
    wb = params["bohrung_schnecke"]
    gb = params["bohrung"]
    pa = params["eingriffswinkel"]
    la = params["steigungswinkel"]
    opt = "true" if params.get("optimiert", True) else "false"

    # Verhindere Division durch Null in OpenSCAD
    if la == 0:
        return f"// {l10n_manager_global.get_string('worm_lead_angle_required')}\n"
    
    display_mode = params.get("paar", "both")
    # Normalisierung für Rückwärts-Kompatibilität
    if isinstance(display_mode, bool):
        display_mode = "both" if display_mode else "gear2"
    
    # Die Schnecke dreht schnell, das Rad langsam (1 Umdrehung pro Z/Gänge)
    # Übersetzung: Winkel_Rad = -Winkel_Schnecke / (Z_Rad / Gänge_Schnecke)
    rot_gear = -anim_angle / (z / ts) 

    code = generate_header()
    
    if display_mode == "gear2":
        # Das Wurmrad ist geometrisch ein Stirnrad mit entgegengesetztem Helixwinkel.
        code += f"// Wurmrad (einzeln)\n"
        code += f"rotate([0, 0, {rot_gear}]) spur_gear({m}, {z}, {w}, {gb}, {pa}, -{la}, {opt});\n"
    elif display_mode in ("both", "gear1"):
        # Positionen wie in gears.scad, damit die Darstellung deckungsgleich ist.
        rad_la = math.radians(la)
        r_worm = (m * ts) / (2 * math.sin(rad_la))
        r_gear = (m * z) / 2
        gamma = -90 * w * math.sin(rad_la) / (math.pi * r_gear)
        tooth_distance = m * math.pi / math.cos(rad_la)
        x = 0.5 if ts % 2 == 0 else 1
        worm_y = (math.ceil(l / (2 * tooth_distance)) - x) * tooth_distance

        # auseinanderziehen, wenn nicht zusammengebaut
        # Das Wurmrad liegt im Referenzsystem bei -r_gear auf X.
        # Skalierter Abstand: abhängig von Radgröße und Modul, mit Mindestabstand,
        # damit kleine und große Geometrien gleich gut getrennt dargestellt werden.
        explode_gap = max(15.0, 0.25 * (2 * r_gear), 6.0 * m)
        explode = 0 if params.get("zusammengebaut", True) else -explode_gap

        if display_mode in ("both", "gear1"):
            code += f"// Schnecke\n"
            # Immer together_built=true verwenden, damit die Schnecke nie geteilt dargestellt wird.
            code += (
                f"translate([{r_worm}, {worm_y}, 0]) "
                f"rotate([90, {180 / ts}, 0]) rotate([0, 0, {anim_angle}]) "
                f"worm({m}, {ts}, {l}, {wb}, {pa}, {la}, true);\n"
            )

        if display_mode == "both":
            code += f"// Wurmrad\n"
            code += (
                f"translate([{-r_gear + explode}, 0, {-w/2}]) "
                f"rotate([0, 0, {gamma + rot_gear}]) "
                f"spur_gear({m}, {z}, {w}, {gb}, {pa}, -{la}, {opt});\n"
            )

    return code

def scad_bevel_gear(params: dict[str, Any], anim_angle: float = 0) -> str:
    # bevel_gear(modul, tooth_number, partial_cone_angle, tooth_width, bore, pressure_angle=20, helix_angle=0)
    m = params["modul"]
    z = params["zahnzahl"]
    pca = params["teilkegelwinkel"]
    tw = params["zahnbreite"]
    d = params["bohrung"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    dir_sign = -1 if params.get("animation_umkehren_einzel", False) else 1
    rot_single = anim_angle * dir_sign
    return (
        generate_header()
        + f"rotate([0, 0, {rot_single}]) bevel_gear({m}, {z}, {pca}, {tw}, {d}, {pa}, {ha});\n"
    )


def _bevel_pair_geometry(m: float, z1: int, z2: int, ang: float) -> dict:
    """Replicate gears.scad bevel_gear_pair geometry in Python for exact positional equivalence."""
    ang_r = math.radians(ang)
    r_gear = m * z1 / 2
    delta_gear = math.degrees(math.atan(math.sin(ang_r) / (z2 / z1 + math.cos(ang_r))))
    delta_pinion = math.degrees(math.atan(math.sin(ang_r) / (z1 / z2 + math.cos(ang_r))))
    rg = r_gear / math.sin(math.radians(delta_gear))
    c = m / 6
    df_pinion = math.pi * rg * delta_pinion / 90 - 2 * (m + c)
    delta_f_pinion = (df_pinion / 2) / (math.pi * rg) * 180
    height_f_pinion = rg * math.cos(math.radians(delta_f_pinion))
    df_gear = math.pi * rg * delta_gear / 90 - 2 * (m + c)
    delta_f_gear = (df_gear / 2) / (math.pi * rg) * 180
    rkf_gear = rg * math.sin(math.radians(delta_f_gear))
    rkf_pinion = rg * math.sin(math.radians(delta_f_pinion))
    height_f_gear = rg * math.cos(math.radians(delta_f_gear))
    # Pinion translation as in gears.scad bevel_gear_pair
    tx = -height_f_pinion * math.cos(math.radians(90 - ang))
    tz = height_f_gear - height_f_pinion * math.sin(math.radians(90 - ang))
    return {
        "delta_gear": delta_gear,
        "delta_pinion": delta_pinion,
        "tx": tx,
        "tz": tz,
        "rkf_gear": rkf_gear,
        "rkf_pinion": rkf_pinion,
        "height_f_gear": height_f_gear,
    }


def scad_bevel_gear_pair(params: dict[str, Any], anim_angle: float = 0) -> str:
    # bevel_gear_pair(modul, gear_teeth, pinion_teeth, axis_angle, tooth_width, gear_bore, pinion_bore, pressure_angle, helix_angle, together_built)
    m = params["modul"]
    z1 = params["zahnzahl"]
    z2 = params["zahnzahl2"]
    ang = params["achswinkel"]
    tw = params["zahnbreite"]
    d1 = params["bohrung"]
    d2 = params["bohrung2"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    dir_sign = -1 if params.get("animation_umkehren", False) else 1
    tb = "true" if params["zusammengebaut"] else "false"

    display_mode = params.get("paar", "both")
    # Normalisierung für Rückwärts-Kompatibilität
    if isinstance(display_mode, bool):
        display_mode = "both" if display_mode else "gear1"

    g = _bevel_pair_geometry(m, z1, z2, ang)
    rot_gear = anim_angle * dir_sign
    # Correct meshing ratio: pinion rotates z1/z2 times faster in opposite direction
    rot_pinion = -rot_gear * (z1 / z2)
    # Phase offset as in gears.scad (180*(1-clearance)/gear_teeth * is_even(pinion_teeth))
    phase = 180 * 0.95 / z1 if z2 % 2 == 0 else 0.0

    code = generate_header()
    
    # Large gear: rotates around its own bore axis (Z) - nur wenn nicht "gear2"
    if display_mode != "gear2":
        code += (
            f"rotate([0, 0, {phase + rot_gear:.6f}]) "
            f"bevel_gear({m}, {z1}, {g['delta_gear']:.6f}, {tw}, {d1}, {pa}, {ha});\n"
        )
    
    # Pinion: nur wenn "both" oder "gear2"
    if display_mode in ("both", "gear2"):
        if params["zusammengebaut"]:
            # Pinion: stable position from Python-computed geometry, rotates around its own bore
            code += (
                f"translate([{g['tx']:.6f}, 0, {g['tz']:.6f}]) "
                f"rotate([0, {ang}, 0]) rotate([0, 0, {rot_pinion:.6f}]) "
                f"bevel_gear({m}, {z2}, {g['delta_pinion']:.6f}, {tw}, {d2}, {pa}, {-ha});\n"
            )
        else:
            sep = g["rkf_pinion"] * 2 + m + g["rkf_gear"]
            code += (
                f"translate([{sep:.6f}, 0, 0]) "
                f"rotate([0, 0, {rot_pinion:.6f}]) "
                f"bevel_gear({m}, {z2}, {g['delta_pinion']:.6f}, {tw}, {d2}, {pa}, {-ha});\n"
            )
    return code


def scad_ring_gear(params: dict[str, Any], anim_angle: float = 0) -> str:
    # ring_gear(modul, zahnzahl, breite, randbreite, eingriffswinkel=20, schraegungswinkel=0)
    m = params["modul"]
    z = params["zahnzahl"]
    b = params["breite"]
    rb = params["randbreite"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    show_inner = params.get("innenzahnrad", False)

    code = generate_header()
    code += f"rotate([0, 0, {anim_angle}]) ring_gear({m}, {z}, {b}, {rb}, {pa}, {ha});\n"

    if show_inner:
        z_inner = params["zahnzahl_innen"]
        bore_inner = params["bohrung_innen"]
        inner_assembled = params.get("zusammengebaut_innen", True)
        inner_phase = meshing_phase_for_even(z_inner)

        # Innenverzahnung: beide Räder drehen gleichsinnig.
        rot_inner = inner_phase + (anim_angle * (z / z_inner))
        if inner_assembled:
            dist = m * (z - z_inner) / 2
            code += (
                f"translate([{dist}, 0, 0]) rotate([0, 0, {rot_inner}]) "
                f"spur_gear({m}, {z_inner}, {b}, {bore_inner}, {pa}, {ha}, true);\n"
            )
        else:
            sep = m * z + m * z_inner / 2 + rb + 5
            code += (
                f"translate([{sep}, 0, 0]) rotate([0, 0, {rot_inner}]) "
                f"spur_gear({m}, {z_inner}, {b}, {bore_inner}, {pa}, {ha}, true);\n"
            )

    return code


def scad_planetary_gear(params: dict[str, Any], anim_angle: float = 0) -> str:
    # planetary_gear(modul, sun_teeth, planet_teeth, number_planets, width, rim_width, bore, pressure_angle, helix_angle, together_built, optimized)
    m = params["modul"]
    st = params["sonne_zähne"]
    pt = params["planet_zähne"]
    np = params["anzahl_planeten"]
    w = params["breite"]
    rw = params["randbreite"]
    d = params["bohrung"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    tb = "true" if params["zusammengebaut"] else "false"
    opt = "true" if params["optimiert"] else "false"

    # Physikalisch korrekte Planetenrad-Animation (Hohlrad fest):
    rt = planetary_ring_teeth(st, pt) # Zähnezahl Hohlrad
    rot_sun = anim_angle
    rot_carrier = anim_angle * st / (st + rt)
    # Planetenrotation relativ zum Steg
    rot_planet_rel = -(anim_angle - rot_carrier) * (st / pt)
    
    dist = planetary_planet_center_distance(m, st, pt)
    
    # Zahnphase-Korrektur für sauberes Eingreifen (parity-aware)
    sun_phase = meshing_phase_for_even(st)
    planet_phase = meshing_phase_for_even(pt)
    
    code = generate_header()
    if params["zusammengebaut"]:
        # Hohlrad (fest)
        code += f"ring_gear({m}, {rt}, {w}, {rw}, {pa}, -{ha});\n"
        # Sonne (dreht sich)
        code += f"rotate([0, 0, {sun_phase + rot_sun}]) spur_gear({m}, {st}, {w}, {d}, {pa}, {ha}, {opt});\n"
        # Planeten
        for i in range(np):
            angle_pos = i * 360 / np + rot_carrier
            code += f"rotate([0, 0, {angle_pos}]) translate([{dist}, 0, 0]) "
            code += f"rotate([0, 0, {planet_phase + rot_planet_rel}]) spur_gear({m}, {pt}, {w}, {d}, {pa}, -{ha}, {opt});\n"
    else:
        # Standard-Library-Aufruf für die Explosionszeichnung/Druck-Layout
        code += f"planetary_gear({m}, {st}, {pt}, {np}, {w}, {rw}, {d}, {pa}, {ha}, {tb}, {opt});\n"
        
    return code

# ---------- GUI-Helfer ----------

class GearTabBase(ttk.Frame):
    MODULE_OPTIONS = (
        "0.25", "0.3", "0.4", "0.5", "0.6", "0.8", "1.0", "1.25",
        "1.5", "2.0", "2.5", "3.0", "4.0", "5.0", "6.0", "8.0", "10.0"
    )

    def __init__(self, master, preview_callback, export_callback, tab_key="gear", **kwargs):
        super().__init__(master, **kwargs)
        self.preview_callback = preview_callback
        self.export_callback = export_callback
        self.entries = {}
        self.tab_key = tab_key
        self.columnconfigure(1, weight=1)
        self.config(padding=10) # Mehr Abstand zum Rand
        self._build_common_buttons()

    def _add_labeled_entry(self, row, key, default="", width=10):
        lbl = ttk.Label(self, text=l10n_manager_global.get_string(key))
        lbl.grid(row=row, column=0, sticky="w", padx=4, pady=5) # Mehr vertikaler Abstand
        var = tk.StringVar(value=str(default))
        entry = ttk.Entry(self, textvariable=var, width=width)
        entry.grid(row=row, column=1, sticky="we", padx=4, pady=5)
        self.entries[key] = {"var": var, "label": lbl, "widget": entry}
        return var

    def _add_labeled_modul_dropdown(self, row, default="1.0", width=10):
        lbl = ttk.Label(self, text=l10n_manager_global.get_string("modul"))
        lbl.grid(row=row, column=0, sticky="w", padx=4, pady=5)

        default_str = str(default)
        if default_str not in self.MODULE_OPTIONS:
            default_str = "1.0"

        var = tk.StringVar(value=default_str)
        combo = ttk.Combobox(self, textvariable=var, values=self.MODULE_OPTIONS, state="readonly", width=width)
        combo.grid(row=row, column=1, sticky="we", padx=4, pady=5)
        self.entries["modul"] = {"var": var, "label": lbl, "widget": combo}
        return var

    def _add_labeled_check(self, row, key, default=True):
        lbl = ttk.Label(self, text=l10n_manager_global.get_string(key))
        lbl.grid(row=row, column=0, sticky="w", padx=4, pady=5)
        var = tk.BooleanVar(value=default)
        cb = ttk.Checkbutton(self, variable=var, text="")
        cb.grid(row=row, column=1, sticky="w", padx=4, pady=5)
        self.entries[key] = {"var": var, "label": lbl, "widget": cb}
        return var

    def _add_labeled_display_mode(self, row, key="gear_display_mode", default="both"):
        """Dropdown für Darstellungsmodus: both, gear1, gear2"""
        lbl = ttk.Label(self, text=l10n_manager_global.get_string(key))
        lbl.grid(row=row, column=0, sticky="w", padx=4, pady=5)
        
        options = ["both", "gear1", "gear2"]
        display_names = [
            l10n_manager_global.get_string("gear_display_both"),
            l10n_manager_global.get_string("gear_display_gear1"),
            l10n_manager_global.get_string("gear_display_gear2"),
        ]
        
        var = tk.StringVar(value=default)
        combo = ttk.Combobox(self, textvariable=var, values=display_names, state="readonly", width=15)
        combo.grid(row=row, column=1, sticky="we", padx=4, pady=5)
        
        # Wrapper: Konvertiere Display-Namen ↔ Werte bei Zugriff
        class DisplayModeVar:
            def __init__(self, string_var, options, display_names):
                self.string_var = string_var
                self.options = options
                self.display_names = display_names
                self._trace_callbacks = []
                
            def get(self):
                display_val = self.string_var.get()
                if display_val in self.display_names:
                    idx = self.display_names.index(display_val)
                    return self.options[idx]
                return "both"  # Fallback
            
            def set(self, value):
                if value in self.options:
                    idx = self.options.index(value)
                    self.string_var.set(self.display_names[idx])
                else:
                    self.string_var.set(self.display_names[0])
            
            def trace_add(self, *args, **kwargs):
                return self.string_var.trace_add(*args, **kwargs)
        
        wrapper_var = DisplayModeVar(var, options, display_names)
        self.entries[key] = {"var": wrapper_var, "label": lbl, "widget": combo}
        return wrapper_var

    def _build_common_buttons(self):
        self.btn_preview = ttk.Button(self, text="", command=self.on_preview, style="Accent.TButton")
        self.btn_export = ttk.Button(self, text="", command=self.on_export)

    def _collect_params(
        self,
        fields: dict[str, tuple[tk.Variable, Callable[[Any], Any]]],
    ) -> dict[str, Any] | None:
        """Zentrale Eingabevalidierung für alle Tabs."""
        try:
            params: dict[str, Any] = {}
            for key, (var, caster) in fields.items():
                params[key] = caster(var.get())
            return params
        except (ValueError, tk.TclError):
            messagebox.showerror(
                l10n_manager_global.get_string("error_title"),
                l10n_manager_global.get_string("error_invalid_input"),
            )
            return None

    def on_preview(self, anim_angle=0):
        scad = self.build_scad(anim_angle=anim_angle)
        if scad is not None:
            self.preview_callback(scad)

    def on_export(self, anim_angle=0):
        scad = self.build_scad()
        if scad is None:
            return

        initial_name = os.path.splitext(self.get_suggested_filename())[0]

        filename = filedialog.asksaveasfilename(
            initialfile=initial_name,
            defaultextension=".scad",
            filetypes=[
                ("OpenSCAD", "*.scad"),
                ("STL (DesignSpark Mechanical)", "*.stl"),
                ("3MF", "*.3mf"),
                ("OFF", "*.off"),
                ("DXF (2D curves for DesignSpark)", "*.dxf"),
                ("Punktekurve TXT", "*.txt"),
                ("Alle Dateien", "*.*"),
            ]
        )
        if not filename:
            return

        ext = os.path.splitext(filename)[1].lower()
        try:
            if ext in ("", ".scad"):
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(scad)
                open_in_openscad(filename)
            elif ext == ".txt":
                export_points_curve_txt(scad, filename)
            else:
                export_scad = as_2d_projection_scad(scad) if ext == ".dxf" else scad
                export_with_openscad(export_scad, filename)
        except Exception as e:
            messagebox.showerror(l10n_manager_global.get_string("error_save_file"), str(e))
            return

    def get_suggested_filename(self):
        """Generiert einen sinnvollen Dateinamen basierend auf Typ und Parametern."""
        # Übersetztes Label als Basis (Leerzeichen durch Unterstrich ersetzen)
        base = l10n_manager_global.get_string(self.tab_key).replace(" ", "_")
        # Sonderzeichen entfernen
        for char in ['/', '\\', '?', '%', '*', ':', '|', '"', '<', '>']:
            base = base.replace(char, '')
            
        try:
            m = f"_m{self.modul.get()}" if hasattr(self, 'modul') else ""
            z_val = ""
            if hasattr(self, 'zahnzahl'): z_val = f"_z{self.zahnzahl.get()}"
            elif hasattr(self, 'z_rad'): z_val = f"_z{self.z_rad.get()}"
            elif hasattr(self, 'st'): z_val = f"_s{self.st.get()}p{self.pt.get()}"
            elif hasattr(self, 'laenge'): z_val = f"_L{self.laenge.get()}"
            
            return f"{base}{m}{z_val}.scad"
        except:
            return f"{base}.scad"

    def build_scad(self, anim_angle=0):
        raise NotImplementedError

    def update_ui_texts(self):
        """Update button texts and entry labels from localization."""
        self.btn_preview.config(text=l10n_manager_global.get_string("preview"))
        self.btn_export.config(text=l10n_manager_global.get_string("export"))
        for key, entry_info in self.entries.items():
            entry_info["label"].config(text=l10n_manager_global.get_string(key))


# ---------- Konkrete Tabs ----------

class SpurGearTab(GearTabBase):
    def __init__(self, master, preview_callback, export_callback, **kwargs):
        super().__init__(master, preview_callback, export_callback, tab_key="spur_gear", **kwargs)
        row = 0
        self.modul = self._add_labeled_modul_dropdown(row, 1.0); row += 1
        self.zahnzahl = self._add_labeled_entry(row, "tooth_number", 30); row += 1
        self.paar = self._add_labeled_display_mode(row, "gear_display_mode", "both"); row += 1
        self.zusammengebaut = self._add_labeled_check(row, "assembled", True); row += 1
        self.z2 = self._add_labeled_entry(row, "tooth_number2", 15); row += 1
        self.breite = self._add_labeled_entry(row, "width", 10); row += 1
        self.bohrung = self._add_labeled_entry(row, "bore", 5); row += 1
        self.eingriffswinkel = self._add_labeled_entry(row, "pressure_angle", 20); row += 1
        self.schraegungswinkel = self._add_labeled_entry(row, "helix_angle", 0); row += 1
        self.profilverschiebung = self._add_labeled_entry(row, "profile_shift", 0.0); row += 1
        self.optimiert = self._add_labeled_check(row, "optimized", True); row += 1

        self.info_label = ttk.Label(self, text="", font=("Segoe UI", 9, "bold"), foreground="blue")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=5); row += 1

        self.btn_preview.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6); row += 1
        self.btn_export.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6)

        for var in [self.modul, self.zahnzahl, self.z2, self.paar, self.profilverschiebung]:
            var.trace_add("write", lambda *args: self.update_info())

        l10n_manager_global.subscribers.append(self.update_ui_texts)
        self.update_ui_texts()

    def update_ui_texts(self):
        super().update_ui_texts()
        self.update_info()

    def update_info(self):
        try:
            m = float(self.modul.get())
            z1 = int(self.zahnzahl.get())
            ps = float(self.profilverschiebung.get())
            display_mode = self.paar.get()
            
            if display_mode != "gear1":
                z2 = int(self.z2.get())
                dist = spur_pair_axis_distance(m, z1, z2, ps)
                ratio_text = format_ratio_text(z2, z1)
                self.info_label.config(text=f"{l10n_manager_global.get_string('axis_distance')} {dist:.2f} mm | {ratio_text}")
            else:
                self.info_label.config(text="")
        except: self.info_label.config(text="")

    def build_scad(self, anim_angle=0):
        params = self._collect_params({
            "modul": (self.modul, float),
            "zahnzahl": (self.zahnzahl, int),
            "paar": (self.paar, str),
            "zusammengebaut": (self.zusammengebaut, bool),
            "zahnzahl2": (self.z2, int),
            "breite": (self.breite, float),
            "bohrung": (self.bohrung, float),
            "eingriffswinkel": (self.eingriffswinkel, float),
            "schraegungswinkel": (self.schraegungswinkel, float),
            "profile_shift": (self.profilverschiebung, float),
            "optimiert": (self.optimiert, bool),
        })
        if params is None:
            return None
        return scad_spur_gear(params, anim_angle=anim_angle)


class HerringboneGearTab(GearTabBase):
    def __init__(self, master, preview_callback, export_callback, **kwargs):
        super().__init__(master, preview_callback, export_callback, tab_key="herringbone_gear", **kwargs)
        row = 0
        self.modul = self._add_labeled_modul_dropdown(row, 1.0); row += 1
        self.zahnzahl = self._add_labeled_entry(row, "tooth_number", 30); row += 1
        self.paar = self._add_labeled_display_mode(row, "gear_display_mode", "both"); row += 1
        self.zusammengebaut = self._add_labeled_check(row, "assembled", True); row += 1
        self.z2 = self._add_labeled_entry(row, "tooth_number2", 15); row += 1
        self.breite = self._add_labeled_entry(row, "width", 10); row += 1
        self.bohrung = self._add_labeled_entry(row, "bore", 5); row += 1
        self.eingriffswinkel = self._add_labeled_entry(row, "pressure_angle", 20); row += 1
        self.schraegungswinkel = self._add_labeled_entry(row, "helix_angle", 45); row += 1
        self.profilverschiebung = self._add_labeled_entry(row, "profile_shift", 0.0); row += 1

        self.info_label = ttk.Label(self, text="", font=("Segoe UI", 9, "bold"), foreground="blue")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=5); row += 1

        self.btn_preview.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6); row += 1
        self.btn_export.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6)

        for var in [self.modul, self.zahnzahl, self.z2, self.paar, self.zusammengebaut, self.profilverschiebung]:
            var.trace_add("write", lambda *args: self.update_info())

        l10n_manager_global.subscribers.append(self.update_ui_texts)
        self.update_ui_texts()

    def update_ui_texts(self):
        super().update_ui_texts()
        self.update_info() # Re-evaluate info label text

    def update_info(self):
        try:
            m = float(self.modul.get())
            z1 = int(self.zahnzahl.get())
            ps = float(self.profilverschiebung.get())
            display_mode = self.paar.get()
            if display_mode != "gear1":
                z2 = int(self.z2.get())
                dist = herringbone_pair_axis_distance(m, z1, z2, ps)
                ratio_text = format_ratio_text(z2, z1)
                self.info_label.config(text=f"{l10n_manager_global.get_string('axis_distance')} {dist:.2f} mm | {ratio_text}")
            else:
                self.info_label.config(text="")
        except: self.info_label.config(text="")

    def build_scad(self, anim_angle=0):
        params = self._collect_params({
            "modul": (self.modul, float),
            "zahnzahl": (self.zahnzahl, int),
            "paar": (self.paar, str),
            "zusammengebaut": (self.zusammengebaut, bool),
            "zahnzahl2": (self.z2, int),
            "breite": (self.breite, float),
            "bohrung": (self.bohrung, float),
            "eingriffswinkel": (self.eingriffswinkel, float),
            "schraegungswinkel": (self.schraegungswinkel, float),
            "profile_shift": (self.profilverschiebung, float),
        })
        if params is None:
            return None
        return scad_herringbone_gear(params, anim_angle=anim_angle)


class RackTab(GearTabBase):
    def __init__(self, master, preview_callback, export_callback, **kwargs):
        super().__init__(master, preview_callback, export_callback, tab_key="rack", **kwargs)
        row = 0
        self.modul = self._add_labeled_modul_dropdown(row, 1.0); row += 1
        self.laenge = self._add_labeled_entry(row, "rack_length", 100); row += 1
        self.hoehe = self._add_labeled_entry(row, "rack_height", 10); row += 1
        self.breite = self._add_labeled_entry(row, "width", 10); row += 1
        self.passendes_zahnrad = self._add_labeled_check(row, "rack_show_matching_gear", False); row += 1
        self.zusammengebaut_ritzel = self._add_labeled_check(row, "rack_pinion_assembled", True); row += 1
        self.zahnzahl_ritzel = self._add_labeled_entry(row, "rack_pinion_teeth", 20); row += 1
        self.bohrung_ritzel = self._add_labeled_entry(row, "rack_pinion_bore", 5); row += 1
        self.eingriffswinkel = self._add_labeled_entry(row, "pressure_angle", 20); row += 1
        self.schraegungswinkel = self._add_labeled_entry(row, "helix_angle", 0); row += 1

        self.info_label = ttk.Label(self, text="", font=("Segoe UI", 9, "bold"), foreground="blue")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=5); row += 1

        self.btn_preview.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6); row += 1
        self.btn_export.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6)

        self.passendes_zahnrad.trace_add("write", lambda *args: self._update_matching_gear_controls())
        for var in [self.modul, self.passendes_zahnrad, self.zahnzahl_ritzel]:
            var.trace_add("write", lambda *args: self.update_info())

        l10n_manager_global.subscribers.append(self.update_ui_texts)
        self.update_ui_texts()

    def update_ui_texts(self):
        super().update_ui_texts()
        self._update_matching_gear_controls()
        self.update_info()

    def _update_matching_gear_controls(self):
        enabled = bool(self.passendes_zahnrad.get())
        state = "normal" if enabled else "disabled"
        self.entries["rack_pinion_assembled"]["widget"].config(state=state)
        self.entries["rack_pinion_teeth"]["widget"].config(state=state)
        self.entries["rack_pinion_bore"]["widget"].config(state=state)

    def update_info(self):
        try:
            if not self.passendes_zahnrad.get():
                self.info_label.config(text="", foreground="blue")
                return
            m = float(self.modul.get())
            z_pinion = int(self.zahnzahl_ritzel.get())
            if z_pinion <= 0:
                self.info_label.config(text=l10n_manager_global.get_string("error_invalid_input"), foreground="red")
                return

            travel = math.pi * m * z_pinion
            ratio_text = format_ratio_text(1, 1)
            self.info_label.config(
                text=f"{ratio_text} | {l10n_manager_global.get_string('rack_motion_ratio', travel=travel)}",
                foreground="blue",
            )
        except:
            self.info_label.config(text="", foreground="blue")

    def build_scad(self, anim_angle=0):
        params = self._collect_params({
            "modul": (self.modul, float),
            "laenge": (self.laenge, float),
            "hoehe": (self.hoehe, float),
            "breite": (self.breite, float),
            "passendes_zahnrad": (self.passendes_zahnrad, bool),
            "eingriffswinkel": (self.eingriffswinkel, float),
            "schraegungswinkel": (self.schraegungswinkel, float),
        })
        if params is None:
            return None
        if params["passendes_zahnrad"]:
            gear_params = self._collect_params({
                "zusammengebaut_ritzel": (self.zusammengebaut_ritzel, bool),
                "zahnzahl_ritzel": (self.zahnzahl_ritzel, int),
                "bohrung_ritzel": (self.bohrung_ritzel, float),
            })
            if gear_params is None:
                return None
            params.update(gear_params)
        return scad_rack(params, anim_angle=anim_angle)


class WormTab(GearTabBase):
    def __init__(self, master, preview_callback, export_callback, **kwargs):
        super().__init__(master, preview_callback, export_callback, tab_key="worm", **kwargs)
        row = 0
        self.modul = self._add_labeled_modul_dropdown(row, 1.0); row += 1
        self.zahnzahl = self._add_labeled_entry(row, "worm_thread_starts", 1); row += 1
        self.breite = self._add_labeled_entry(row, "worm_length", 40); row += 1
        self.bohrung = self._add_labeled_entry(row, "worm_bore", 2); row += 1
        self.eingriffswinkel = self._add_labeled_entry(row, "worm_pressure_angle", 20); row += 1
        self.schraegungswinkel = self._add_labeled_entry(row, "worm_lead_angle", 10); row += 1
        self.zusammengebaut = self._add_labeled_check(row, "worm_assembled", True); row += 1

        self.info_label = ttk.Label(self, text="", font=("Segoe UI", 9, "bold"), foreground="blue")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=5); row += 1

        self.btn_preview.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6); row += 1
        self.btn_export.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6)

        for var in [self.modul, self.zahnzahl, self.schraegungswinkel, self.bohrung, self.zusammengebaut]:
            var.trace_add("write", lambda *args: (self.update_info(), self.on_preview()))

        l10n_manager_global.subscribers.append(self.update_ui_texts)
        self.update_ui_texts()

    def update_ui_texts(self):
        super().update_ui_texts()
        self.update_info()

    def update_info(self):
        try:
            m = float(self.modul.get())
            ts = int(self.zahnzahl.get())
            la = float(self.schraegungswinkel.get())
            d = float(self.bohrung.get())

            if la <= 0:
                self.info_label.config(text=l10n_manager_global.get_string('worm_lead_angle_required'), foreground="red")
                return

            sin_la = math.sin(math.radians(la))
            if sin_la <= 0:
                self.info_label.config(text=l10n_manager_global.get_string('worm_lead_angle_required'), foreground="red")
                return

            # Grenzwert aus Bibliotheksgeometrie: bore < 2 * (r - modul - modul/6)
            max_bore = worm_root_diameter(m, ts, la)

            if d >= max_bore:
                self.info_label.config(
                    text=l10n_manager_global.get_string(
                        'worm_bore_too_large',
                        bore=f"{d:.2f}",
                        max_bore=f"{max_bore:.2f}",
                    ),
                    foreground="orange",
                )
            else:
                self.info_label.config(text="", foreground="blue")
        except: self.info_label.config(text="")

    def build_scad(self, anim_angle=0):
        params = self._collect_params({
            "modul": (self.modul, float),
            "zahnzahl": (self.zahnzahl, int),
            "breite": (self.breite, float),
            "bohrung": (self.bohrung, float),
            "eingriffswinkel": (self.eingriffswinkel, float),
            "schraegungswinkel": (self.schraegungswinkel, float),
            "zusammengebaut": (self.zusammengebaut, bool),
        })
        if params is None:
            return None
        return scad_worm(params, anim_angle=anim_angle)


class WormGearTab(GearTabBase):
    def __init__(self, master, preview_callback, export_callback, **kwargs):
        super().__init__(master, preview_callback, export_callback, tab_key="worm_gear", **kwargs)
        row = 0
        self.modul = self._add_labeled_modul_dropdown(row, 1.0); row += 1
        self.z_rad = self._add_labeled_entry(row, "worm_gear_teeth", 30); row += 1
        self.paar = self._add_labeled_display_mode(row, "gear_display_mode", "both"); row += 1
        self.zusammengebaut = self._add_labeled_check(row, "worm_assembled", True); row += 1
        self.thread_starts = self._add_labeled_entry(row, "worm_thread_starts_label", 2); row += 1
        self.laenge_schnecke = self._add_labeled_entry(row, "worm_length_label", 20); row += 1
        self.bohrung_schnecke = self._add_labeled_entry(row, "worm_worm_bore", 4); row += 1
        self.breite = self._add_labeled_entry(row, "worm_gear_width", 10); row += 1
        self.bohrung_rad = self._add_labeled_entry(row, "worm_gear_bore", 5); row += 1
        self.eingriffswinkel = self._add_labeled_entry(row, "pressure_angle", 20); row += 1
        self.steigungswinkel = self._add_labeled_entry(row, "worm_lead_angle", 10); row += 1
        self.opt = self._add_labeled_check(row, "worm_optimized", True); row += 1

        self.info_label = ttk.Label(self, text="", font=("Segoe UI", 9, "bold"), foreground="blue")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=5); row += 1

        self.btn_preview.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6); row += 1
        self.btn_export.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6)

        for var in [self.modul, self.z_rad, self.thread_starts, self.steigungswinkel, self.paar, self.zusammengebaut]:
            var.trace_add("write", lambda *args: self.update_info())

        l10n_manager_global.subscribers.append(self.update_ui_texts)
        self.update_ui_texts()

    def update_ui_texts(self):
        super().update_ui_texts()
        self.update_info() # Re-evaluate info label text

    def update_info(self):
        try:
            m = float(self.modul.get())
            z_gear = int(self.z_rad.get())
            ts = int(self.thread_starts.get())
            la = float(self.steigungswinkel.get())

            if z_gear <= 0 or ts <= 0:
                self.info_label.config(text=l10n_manager_global.get_string("error_invalid_input"), foreground="red")
                return

            ratio_text = format_ratio_text(z_gear, ts)

            if self.paar.get():
                try:
                    dist = worm_axis_distance(m, ts, la, z_gear)
                    self.info_label.config(
                        text=f"{l10n_manager_global.get_string('worm_axis_distance')} {dist:.2f} mm | {ratio_text}",
                        foreground="blue",
                    )
                except ValueError:
                    self.info_label.config(text=l10n_manager_global.get_string('worm_lead_angle_required'), foreground="red")
            else:
                self.info_label.config(text=ratio_text, foreground="blue")
        except: self.info_label.config(text="")

    def build_scad(self, anim_angle=0):
        params = self._collect_params({
            "modul": (self.modul, float),
            "zahnzahl": (self.z_rad, int),
            "paar": (self.paar, str),
            "zusammengebaut": (self.zusammengebaut, bool),
            "thread_starts": (self.thread_starts, int),
            "laenge_schnecke": (self.laenge_schnecke, float),
            "bohrung_schnecke": (self.bohrung_schnecke, float),
            "breite": (self.breite, float),
            "bohrung": (self.bohrung_rad, float),
            "eingriffswinkel": (self.eingriffswinkel, float),
            "steigungswinkel": (self.steigungswinkel, float),
            "optimiert": (self.opt, bool),
        })
        if params is None:
            return None
        return scad_worm_gear(params, anim_angle=anim_angle)


class RingGearTab(GearTabBase):
    def __init__(self, master, preview_callback, export_callback, **kwargs):
        super().__init__(master, preview_callback, export_callback, tab_key="ring_gear", **kwargs)
        row = 0
        self.modul = self._add_labeled_modul_dropdown(row, 1.0); row += 1
        self.zahnzahl = self._add_labeled_entry(row, "tooth_number", 30); row += 1
        self.breite = self._add_labeled_entry(row, "width", 10); row += 1
        self.randbreite = self._add_labeled_entry(row, "ring_rim_width", 5); row += 1
        self.innenzahnrad = self._add_labeled_check(row, "ring_show_inner_gear", False); row += 1
        self.innen_zahnzahl = self._add_labeled_entry(row, "ring_inner_teeth", 20); row += 1
        self.innen_bohrung = self._add_labeled_entry(row, "ring_inner_bore", 5); row += 1
        self.innen_zusammengebaut = self._add_labeled_check(row, "ring_inner_assembled", True); row += 1
        self.eingriffswinkel = self._add_labeled_entry(row, "pressure_angle", 20); row += 1
        self.schraegungswinkel = self._add_labeled_entry(row, "helix_angle", 0); row += 1

        self.info_label = ttk.Label(self, text="", font=("Segoe UI", 9, "bold"), foreground="blue")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=5); row += 1

        self.btn_preview.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6); row += 1
        self.btn_export.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6)

        self.innenzahnrad.trace_add("write", lambda *args: self._update_inner_gear_controls())
        for var in [self.modul, self.zahnzahl, self.innenzahnrad, self.innen_zahnzahl]:
            var.trace_add("write", lambda *args: self.update_info())

        l10n_manager_global.subscribers.append(self.update_ui_texts)
        self.update_ui_texts()

    def update_ui_texts(self):
        super().update_ui_texts()
        self._update_inner_gear_controls()
        self.update_info()

    def _update_inner_gear_controls(self):
        enabled = bool(self.innenzahnrad.get())
        state = "normal" if enabled else "disabled"
        self.entries["ring_inner_teeth"]["widget"].config(state=state)
        self.entries["ring_inner_bore"]["widget"].config(state=state)
        self.entries["ring_inner_assembled"]["widget"].config(state=state)

    def update_info(self):
        try:
            if not self.innenzahnrad.get():
                self.info_label.config(text="", foreground="blue")
                return
            m = float(self.modul.get())
            z_ring = int(self.zahnzahl.get())
            z_inner = int(self.innen_zahnzahl.get())
            try:
                dist = ring_inner_axis_distance(m, z_ring, z_inner)
            except ValueError:
                self.info_label.config(text=l10n_manager_global.get_string("error_invalid_input"), foreground="red")
                return
            ratio_text = format_ratio_text(z_ring, z_inner)
            self.info_label.config(
                text=f"{l10n_manager_global.get_string('axis_distance')} {dist:.2f} mm | {ratio_text}",
                foreground="blue",
            )
        except:
            self.info_label.config(text="", foreground="blue")

    def build_scad(self, anim_angle=0):
        params = self._collect_params({
            "modul": (self.modul, float),
            "zahnzahl": (self.zahnzahl, int),
            "breite": (self.breite, float),
            "randbreite": (self.randbreite, float),
            "innenzahnrad": (self.innenzahnrad, bool),
            "eingriffswinkel": (self.eingriffswinkel, float),
            "schraegungswinkel": (self.schraegungswinkel, float),
        })
        if params is None:
            return None
        if params["innenzahnrad"]:
            inner_params = self._collect_params({
                "zahnzahl_innen": (self.innen_zahnzahl, int),
                "bohrung_innen": (self.innen_bohrung, float),
                "zusammengebaut_innen": (self.innen_zusammengebaut, bool),
            })
            if inner_params is None:
                return None
            params.update(inner_params)
            if params["zahnzahl_innen"] <= 0 or params["zahnzahl_innen"] >= params["zahnzahl"]:
                messagebox.showerror(
                    l10n_manager_global.get_string("error_title"),
                    l10n_manager_global.get_string("error_invalid_input"),
                )
                return None
        return scad_ring_gear(params, anim_angle=anim_angle)


class PlanetaryGearTab(GearTabBase):
    def __init__(self, master, preview_callback, export_callback, **kwargs):
        super().__init__(master, preview_callback, export_callback, tab_key="planetary_gear", **kwargs)
        row = 0
        self.modul = self._add_labeled_modul_dropdown(row, 1.0); row += 1
        self.st = self._add_labeled_entry(row, "planetary_sun_teeth", 16); row += 1
        self.pt = self._add_labeled_entry(row, "planetary_planet_teeth", 9); row += 1
        self.np = self._add_labeled_entry(row, "planetary_num_planets", 5); row += 1
        self.breite = self._add_labeled_entry(row, "width", 5); row += 1
        self.rand = self._add_labeled_entry(row, "planetary_rim_width", 3); row += 1
        self.bohrung = self._add_labeled_entry(row, "bore", 4); row += 1
        self.pa = self._add_labeled_entry(row, "pressure_angle", 20); row += 1
        self.ha = self._add_labeled_entry(row, "helix_angle", 0); row += 1
        self.tb = self._add_labeled_check(row, "planetary_assembled", True); row += 1
        self.opt = self._add_labeled_check(row, "planetary_optimized", True); row += 1

        # Info-Label für Plausibilität
        self.info_label = ttk.Label(self, text="", font=("Segoe UI", 9, "bold"))
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=5); row += 1

        self.btn_fix_planets = ttk.Button(self, text="", command=self.fix_planets) # Text set in update_ui_texts
        self.btn_fix_planets.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=2); row += 1

        self.btn_preview.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6); row += 1
        self.btn_export.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6)

        # Traces für Echtzeit-Check hinzufügen
        for var in [self.st, self.pt, self.np]:
            var.trace_add("write", lambda *args: self.validate_planetary())
        
        self.validate_planetary()
        l10n_manager_global.subscribers.append(self.update_ui_texts)
        self.update_ui_texts() # Initial update

    def update_ui_texts(self):
        super().update_ui_texts()
        self.btn_fix_planets.config(text=l10n_manager_global.get_string("planetary_optimize_planets"))
        self.validate_planetary() # Re-evaluate info label text

    def validate_planetary(self):
        try:
            st = int(self.st.get())
            pt = int(self.pt.get())
            n = int(self.np.get())
            
            # Berechnung Hohlrad und Übersetzung
            rt = planetary_ring_teeth(st, pt)  # Zähnezahl Hohlrad
            total_sum = st + rt # Zs + Zr
            
            # i = (Zs + Zr) / Zs (Sonne=Eingang, Steg=Ausgang, Hohlrad=fest)
            ratio = total_sum / st
            divisor = math.gcd(total_sum, st)
            out_reduced = total_sum // divisor
            in_reduced = st // divisor
            
            # Bedingung für symmetrische Montage: (Zs + Zr) / N muss Ganzzahl sein
            assemblable = total_sum % n == 0
            
            # Bedingung für Kollision (max Planeten)
            max_n = int(180 / math.degrees(math.asin(pt / (st + pt))))
            
            # Suche nach gültigen Planetenanzahlen für Vorschläge
            valid_ns = [i for i in range(2, max_n + 1) if total_sum % i == 0]
            
            msg = l10n_manager_global.get_string(
                "planetary_info_ring_gear",
                rt=rt,
                ratio=ratio,
                out=out_reduced,
                inp=in_reduced,
            ) + "\n"
            
            if not assemblable:
                msg += l10n_manager_global.get_string("planetary_info_assembly_error", total_sum=total_sum, n=n) + "\n"
                if valid_ns:
                    msg += l10n_manager_global.get_string("planetary_info_possible_n", valid_ns=', '.join(map(str, valid_ns)))
                else:
                    msg += l10n_manager_global.get_string("planetary_info_no_symmetric_assembly")
            if n > max_n:
                msg += l10n_manager_global.get_string("planetary_info_collision", max_n=max_n)
            elif assemblable:
                msg += l10n_manager_global.get_string("planetary_info_plausible")
            
            self.info_label.config(
                text=msg, 
                foreground="red" if not assemblable or n > max_n else "#008000"
            )
        except:
            self.info_label.config(text=l10n_manager_global.get_string("planetary_info_check_input"), foreground="orange")

    def fix_planets(self):
        """Sucht die nächstgelegene gültige Planetenanzahl und setzt diese automatisch."""
        try:
            st = int(self.st.get())
            pt = int(self.pt.get())
            n_current = int(self.np.get())
            total_sum = st + (st + 2 * pt)
            max_n = int(180 / math.degrees(math.asin(pt / (st + pt))))
            valid_ns = [i for i in range(2, max_n + 1) if total_sum % i == 0]
            if valid_ns:
                # Den Wert finden, der dem aktuellen N am nächsten kommt
                best_n = min(valid_ns, key=lambda x: abs(x - n_current))
                self.np.set(str(best_n))
        except: pass
        
    def build_scad(self, anim_angle=0):
        params = self._collect_params({
            "modul": (self.modul, float),
            "sonne_zähne": (self.st, int),
            "planet_zähne": (self.pt, int),
            "anzahl_planeten": (self.np, int),
            "breite": (self.breite, float),
            "randbreite": (self.rand, float),
            "bohrung": (self.bohrung, float),
            "eingriffswinkel": (self.pa, float),
            "schraegungswinkel": (self.ha, float),
            "zusammengebaut": (self.tb, bool),
            "optimiert": (self.opt, bool),
        })
        if params is None:
            return None
        return scad_planetary_gear(params, anim_angle=anim_angle)


class BevelGearTab(GearTabBase):
    def __init__(self, master, preview_callback, export_callback, **kwargs):
        super().__init__(master, preview_callback, export_callback, tab_key="bevel_gear", **kwargs)
        row = 0
        self.modul = self._add_labeled_modul_dropdown(row, 1.0); row += 1
        self.zahnzahl = self._add_labeled_entry(row, "bevel_gear_teeth", 30); row += 1
        self.paar = self._add_labeled_display_mode(row, "gear_display_mode", "both"); row += 1
        self.z2 = self._add_labeled_entry(row, "bevel_pinion_teeth", 11); row += 1
        self.achswinkel = self._add_labeled_entry(row, "bevel_axis_angle", 90); row += 1
        self.teilkegelwinkel = self._add_labeled_entry(row, "bevel_partial_cone_angle", 45); row += 1
        self.zahnbreite = self._add_labeled_entry(row, "bevel_tooth_width", 8); row += 1
        self.bohrung = self._add_labeled_entry(row, "bevel_bore1", 5); row += 1
        self.bohrung2 = self._add_labeled_entry(row, "bevel_bore2", 4); row += 1
        self.pa = self._add_labeled_entry(row, "pressure_angle", 20); row += 1
        self.ha = self._add_labeled_entry(row, "helix_angle", 0); row += 1
        self.tb = self._add_labeled_check(row, "bevel_assembled", True); row += 1
        self.anim_reverse = self._add_labeled_check(row, "bevel_reverse_animation", False); row += 1
        self.anim_reverse_single = self._add_labeled_check(row, "bevel_reverse_animation_single", False); row += 1

        self.info_label = ttk.Label(self, text="", font=("Segoe UI", 9, "bold"), foreground="blue")
        self.info_label.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=5); row += 1

        self.btn_preview.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6); row += 1
        self.btn_export.grid(row=row, column=0, columnspan=2, sticky="we", padx=4, pady=6)

        for var in [self.zahnzahl, self.z2, self.paar]:
            var.trace_add("write", lambda *args: self.update_info())

        l10n_manager_global.subscribers.append(self.update_ui_texts)
        self.update_ui_texts()

    def update_ui_texts(self):
        super().update_ui_texts()
        self.update_info()

    def update_info(self):
        try:
            display_mode = self.paar.get()
            if display_mode == "gear1":
                self.info_label.config(text="", foreground="blue")
                return
            z1 = int(self.zahnzahl.get())
            z2 = int(self.z2.get())
            if z1 <= 0 or z2 <= 0:
                self.info_label.config(text=l10n_manager_global.get_string("error_invalid_input"), foreground="red")
                return
            ratio_text = format_ratio_text(z2, z1)
            self.info_label.config(text=ratio_text, foreground="blue")
        except:
            self.info_label.config(text="", foreground="blue")

    def build_scad(self, anim_angle=0):
        params = self._collect_params({
            "modul": (self.modul, float),
            "zahnzahl": (self.zahnzahl, int),
            "paar": (self.paar, str),
            "zahnzahl2": (self.z2, int),
            "achswinkel": (self.achswinkel, float),
            "teilkegelwinkel": (self.teilkegelwinkel, float),
            "zahnbreite": (self.zahnbreite, float),
            "bohrung": (self.bohrung, float),
            "bohrung2": (self.bohrung2, float),
            "eingriffswinkel": (self.pa, float),
            "schraegungswinkel": (self.ha, float),
            "zusammengebaut": (self.tb, bool),
            "animation_umkehren": (self.anim_reverse, bool),
            "animation_umkehren_einzel": (self.anim_reverse_single, bool),
        })
        if params is None:
            return None
        if params["paar"]:
            return scad_bevel_gear_pair(params, anim_angle=anim_angle)
        return scad_bevel_gear(params, anim_angle=anim_angle)


# ---------- Haupt-GUI ----------

class GearGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        global l10n_manager_global
        self.l = LocalizationManager(resource_path("lang.ini"))
        l10n_manager_global = self.l # Assign the instance to the global variable

        self.title(self.l.get_string("app_title"))
        self.geometry("1200x780")
        self.minsize(980, 680)
        self.preview_bg = "#d8e6f7"

        if not check_paths():
            # trotzdem starten, damit man Pfade anpassen kann
            pass

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Den Hintergrund des Hauptfensters auf weiß setzen
        main = ttk.Panedwindow(self, orient="horizontal")
        main.grid(row=0, column=0, sticky="nsew")

        # Links: Tabs
        left = ttk.Frame(main)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)
        notebook = ttk.Notebook(left)
        notebook.grid(row=0, column=0, sticky="nsew")
        
        self.last_scad_code = "" 
        self.last_mouse_x = 0
        self.last_mouse_y = 0
        self._refresh_timer = None
        self.x_rotation_var = tk.DoubleVar(value=60) # Start-Neigung
        self.cam_x_var = tk.DoubleVar(value=0)
        self.cam_y_var = tk.DoubleVar(value=0)
        self.last_w = 0
        self.last_h = 0
        self.animation_angle = 0.0
        self.animate_preview_var = tk.BooleanVar(value=False)
        self.animation_job_id = None # Speichert die ID des self.after-Aufrufs für die Animation
        self.render_thread = None # Speichert den aktuellen Rendering-Thread

        # Rechts: Vorschau (Zuerst das Panedwindow erstellen!)
        right_pane = ttk.Panedwindow(main, orient="vertical")

        # Kamera-Steuerung
        camera_controls_frame = ttk.LabelFrame(right_pane, text="Kamera-Steuerung", padding=10)
        self.camera_frame = camera_controls_frame
        camera_controls_frame.columnconfigure(1, weight=1)

        self.z_rotation_var = tk.DoubleVar(value=45) # Standard isometrische Z-Rotation
        ttk.Label(camera_controls_frame, text="Z-Rotation:").grid(row=0, column=0, sticky="w", padx=2, pady=2)
        self.z_rotation_scale = ttk.Scale(camera_controls_frame, from_=0, to=360, orient="horizontal",
                                          variable=self.z_rotation_var, command=self._on_camera_param_change)
        self.z_rotation_scale.grid(row=0, column=1, sticky="ew", padx=2, pady=2)

        self.camera_distance_var = tk.DoubleVar(value=200) # Standard Kamera-Distanz
        self.zoom_lbl = ttk.Label(camera_controls_frame, text="Zoom (Distanz):")
        self.zoom_lbl.grid(row=1, column=0, sticky="w", padx=2, pady=2)
        self.camera_distance_scale = ttk.Scale(camera_controls_frame, from_=50, to=1000, orient="horizontal",
                                               variable=self.camera_distance_var, command=self._on_camera_param_change)
        self.camera_distance_scale.grid(row=1, column=1, sticky="ew", padx=2, pady=2)

        self.reset_view_button = ttk.Button(camera_controls_frame, text="", command=self._reset_camera_view)
        self.reset_view_button.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=5)

        self.animate_preview_check = ttk.Checkbutton(camera_controls_frame, text="", variable=self.animate_preview_var, command=self._toggle_animation)
        self.animate_preview_check.grid(row=3, column=0, columnspan=2, sticky="ew", padx=2, pady=5)

        # Bild-Vorschau oben
        self.preview_frame = ttk.Frame(right_pane)
        # Wir nutzen ein tk.Frame für eine einfachere Hintergrundsteuerung
        self.preview_frame = tk.Frame(right_pane, bg=self.preview_bg)
        self.preview_frame.columnconfigure(0, weight=1)
        self.preview_frame.rowconfigure(0, weight=1)
        self.img_label = ttk.Label(self.preview_frame, text=self.l.get_string("preview_loading"))
        self.img_label = tk.Label(self.preview_frame, text=self.l.get_string("preview_loading"), bg=self.preview_bg)
        self.img_label.grid(row=0, column=0, sticky="nsew")
        self.preview_frame.bind("<Configure>", self._on_resize)

        # Maus-Bindungen für die Vorschau
        self.img_label.bind("<ButtonPress-1>", self._on_mouse_down)
        self.img_label.bind("<B1-Motion>", self._on_mouse_drag)
        self.img_label.bind("<ButtonPress-3>", self._on_mouse_down)
        self.img_label.bind("<B3-Motion>", self._on_mouse_drag_pan)
        self.img_label.bind("<MouseWheel>", self._on_mouse_wheel)
        self.img_label.bind("<Button-4>", self._on_mouse_wheel) # Linux Scroll Up
        self.img_label.bind("<Button-5>", self._on_mouse_wheel) # Linux Scroll Down
        
        # Text-Vorschau unten
        text_frame = ttk.Frame(right_pane)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(1, weight=1)
        self.scad_lbl = ttk.Label(text_frame, text="")
        self.scad_lbl.grid(row=0, column=0, sticky="w", padx=4, pady=2)

        self.preview = tk.Text(text_frame, wrap="none", font=("Consolas", 9), height=10)
        self.preview.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        yscroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.preview.yview)
        yscroll.grid(row=1, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=yscroll.set)

        xscroll = ttk.Scrollbar(text_frame, orient="horizontal", command=self.preview.xview)
        xscroll.grid(row=2, column=0, sticky="ew")
        self.preview.configure(xscrollcommand=xscroll.set)

        right_pane.add(camera_controls_frame, weight=0)
        right_pane.add(self.preview_frame, weight=3) # Bild-Vorschau unter Kamera-Steuerung
        right_pane.add(text_frame, weight=1) # Text-Vorschau unten
        
        main.add(left, weight=1)
        main.add(right_pane, weight=1)

        self._setup_style()
        self._setup_menus()

        def set_preview(text):
            self.preview.delete("1.0", tk.END)
            self.preview.insert("1.0", text)
            self.update_image_preview(text)
            self.last_scad_code = text # Speichere den SCAD-Code

        self.all_tabs = []
        def dummy_export(_):
            pass  # Export wird in den Tabs selbst gehandhabt

        # Tabs hinzufügen (Hier im __init__!)
        spur_tab = SpurGearTab(notebook, set_preview, dummy_export)
        herring_tab = HerringboneGearTab(notebook, set_preview, dummy_export)
        rack_tab = RackTab(notebook, set_preview, dummy_export)
        worm_tab = WormTab(notebook, set_preview, dummy_export)
        wormgear_tab = WormGearTab(notebook, set_preview, dummy_export)
        ring_tab = RingGearTab(notebook, set_preview, dummy_export)
        planetary_tab = PlanetaryGearTab(notebook, set_preview, dummy_export)
        bevel_tab = BevelGearTab(notebook, set_preview, dummy_export)
        
        self.all_tabs.extend([spur_tab, herring_tab, rack_tab, worm_tab, wormgear_tab, ring_tab, planetary_tab, bevel_tab])

        self.notebook = notebook
        notebook.add(spur_tab, text="")
        notebook.add(herring_tab, text="")
        notebook.add(rack_tab, text="")
        notebook.add(worm_tab, text="")
        notebook.add(wormgear_tab, text="")
        notebook.add(ring_tab, text="")
        notebook.add(planetary_tab, text="")
        notebook.add(bevel_tab, text="")

        self.l.subscribers.append(self.update_ui_texts)
        self.update_ui_texts()

    def update_ui_texts(self):
        self.title(self.l.get_string("app_title"))
        self.menubar.entryconfig(1, label=self.l.get_string("file_menu"))
        self.menubar.entryconfig(2, label=self.l.get_string("help_menu"))
        self.menubar.entryconfig(3, label=self.l.get_string("language_menu"))
        
        # Menü-Einträge aktualisieren
        self.file_menu.entryconfig(0, label=self.l.get_string("file_menu_exit"))
        self.help_menu.entryconfig(0, label=self.l.get_string("help_menu_about"))
        self.language_menu.entryconfig(0, label=self.l.get_string("language_german"))
        self.language_menu.entryconfig(1, label=self.l.get_string("language_english"))
        self.language_menu.entryconfig(2, label=self.l.get_string("language_russian"))
        
        self.camera_frame.config(text=self.l.get_string("camera_controls"))
        self.zoom_lbl.config(text=self.l.get_string("zoom_distance"))
        self.scad_lbl.config(text=self.l.get_string("scad_code"))
        self.reset_view_button.config(text=self.l.get_string("reset_view"))
        self.animate_preview_check.config(text=self.l.get_string("animate_preview"))
        if not self.last_scad_code:
            self.img_label.config(text=self.l.get_string("preview_loading"))

        tabs_keys = ["spur_gear", "herringbone_gear", "rack", "worm", "worm_gear", "ring_gear", "planetary_gear", "bevel_gear"]
        for i, key in enumerate(tabs_keys):
            self.notebook.tab(i, text=self.l.get_string(key))

        for tab in self.all_tabs:
            tab.update_ui_texts()

    def _setup_style(self):
        self.style = ttk.Style(self)
        # Modernes helles Thema mit klaren Kontrasten
        bg_color = "#f3f6fb"
        surface_color = "#ffffff"
        secondary_bg = "#eaf0f7"
        accent_color = "#0f6cbd"
        accent_hover = "#115ea3"
        text_color = "#13233a"
        border_color = "#d7e2ee"

        self.style.theme_use("clam")
        self.style.configure("TFrame", background=bg_color)
        self.style.configure("Card.TFrame", background=surface_color)
        self.style.configure("TLabel", background=bg_color, foreground=text_color, font=("Segoe UI Variable Small", 10))
        self.style.configure("Title.TLabel", background=surface_color, foreground="#0c3b66", font=("Segoe UI Semibold", 13))
        self.style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(10, 7), borderwidth=0)
        self.style.map("TButton", background=[("active", "#dde8f5")])
        
        self.style.configure("TLabelframe", background=bg_color, bordercolor=border_color, relief="flat", borderwidth=1)
        self.style.configure("TLabelframe.Label", background=bg_color, foreground=accent_color, font=("Segoe UI Variable Small", 10, "bold"))

        self.style.configure("TEntry", fieldbackground=surface_color, foreground=text_color, bordercolor=border_color, insertcolor=text_color, padding=4)
        self.style.map("TEntry", bordercolor=[("focus", accent_color)])
        self.style.configure("TCombobox", fieldbackground=surface_color, background=surface_color, foreground=text_color, bordercolor=border_color, arrowsize=14)
        self.style.map("TCombobox", bordercolor=[("focus", accent_color)])
        self.style.configure("TCheckbutton", background=bg_color, foreground=text_color)
        
        self.style.configure("TNotebook", background=bg_color, borderwidth=0, tabmargins=[8, 8, 8, 0])
        self.style.configure("TNotebook.Tab", background=secondary_bg, foreground=text_color, padding=[16, 8], font=("Segoe UI Variable Small", 9, "bold"))
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", surface_color), ("active", "#dce8f6")],
            foreground=[("selected", accent_color)]
        )
        
        self.style.configure("Accent.TButton", foreground="white", background=accent_color)
        self.style.map("Accent.TButton", background=[("active", accent_hover)])
        self.style.configure("TScale", background=bg_color)
        self.style.configure("TPanedwindow", background=bg_color)

        self.option_add("*Menu.background", surface_color)
        self.option_add("*Menu.foreground", text_color)
        self.option_add("*Menu.activeBackground", "#dce8f6")
        self.option_add("*Menu.activeForeground", text_color)
        self.configure(background=bg_color)

    def _setup_menus(self):
        self.menubar = tk.Menu(self, tearoff=0)
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label=self.l.get_string("file_menu_exit"), command=self.quit)
        self.menubar.add_cascade(label="", menu=self.file_menu)
        
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.help_menu.add_command(label=self.l.get_string("help_menu_about"), command=self.show_about)
        self.menubar.add_cascade(label="", menu=self.help_menu)

        self.language_menu = tk.Menu(self.menubar, tearoff=0)
        self.language_menu.add_command(label=self.l.get_string("language_german"), command=lambda: self.l.set_language('de'))
        self.language_menu.add_command(label=self.l.get_string("language_english"), command=lambda: self.l.set_language('en'))
        self.language_menu.add_command(label=self.l.get_string("language_russian"), command=lambda: self.l.set_language('ru'))
        self.menubar.add_cascade(label="", menu=self.language_menu)
        self.config(menu=self.menubar)

    def show_about(self):
        about_win = tk.Toplevel(self)
        about_win.title(self.l.get_string("about_title"))
        about_win.transient(self)
        about_win.resizable(False, False)
        about_win.configure(bg="#f3f6fb")

        container = ttk.Frame(about_win, style="Card.TFrame", padding=16)
        container.grid(row=0, column=0, padx=14, pady=14, sticky="nsew")
        container.columnconfigure(0, weight=1)

        title_lbl = ttk.Label(container, text=self.l.get_string("about_title"), style="Title.TLabel")
        title_lbl.grid(row=0, column=0, sticky="w")

        msg_lbl = ttk.Label(
            container,
            text=self.l.get_string("about_message"),
            justify="left",
            wraplength=560,
            background="#ffffff",
            foreground="#13233a",
        )
        msg_lbl.grid(row=1, column=0, sticky="w", pady=(10, 12))

        close_btn = ttk.Button(container, text="OK", style="Accent.TButton", command=about_win.destroy)
        close_btn.grid(row=2, column=0, sticky="e")

        about_win.update_idletasks()
        width = about_win.winfo_width()
        height = about_win.winfo_height()
        x = self.winfo_rootx() + (self.winfo_width() - width) // 2
        y = self.winfo_rooty() + (self.winfo_height() - height) // 2
        about_win.geometry(f"+{x}+{y}")
        about_win.grab_set()

    def _on_camera_param_change(self, event=None):
        """Triggered by sliders or mouse, with throttling."""
        if self._refresh_timer is not None:
            self.after_cancel(self._refresh_timer)
        self._refresh_timer = self.after(100, lambda: self.update_image_preview(self.last_scad_code))
        # update_image_preview wird das Stoppen/Neustarten der Animation übernehmen, falls animate_preview_var True ist.

    def _on_resize(self, event):
        """Wird aufgerufen, wenn das Vorschaufenster in der Größe geändert wird."""
        # Nur neu rendern, wenn sich die Größe signifikant geändert hat
        if abs(self.last_w - event.width) < 20 and abs(self.last_h - event.height) < 20:
            return
        self.last_w = event.width
        self.last_h = event.height
        if self.last_scad_code:
            self._on_camera_param_change()

    def _on_mouse_down(self, event):
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y

    def _on_mouse_drag(self, event):
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        
        # Update Rotation (Z = Horizontal ziehen, X = Vertikal ziehen)
        self.z_rotation_var.set((self.z_rotation_var.get() + dx) % 360)
        new_x = self.x_rotation_var.get() + dy
        self.x_rotation_var.set(max(0, min(90, new_x))) # Begrenzung der Neigung
        
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        self._on_camera_param_change()

    def _on_mouse_drag_pan(self, event):
        dx = event.x - self.last_mouse_x
        dy = event.y - self.last_mouse_y
        
        # Empfindlichkeit basierend auf Distanz (Zoom) anpassen
        factor = self.camera_distance_var.get() / 500.0
        
        # Verschiebung berechnen
        self.cam_x_var.set(self.cam_x_var.get() - dx * factor)
        self.cam_y_var.set(self.cam_y_var.get() + dy * factor)
        
        self.last_mouse_x = event.x
        self.last_mouse_y = event.y
        self._on_camera_param_change()

    def _on_mouse_wheel(self, event):
        # Windows delta ist meist 120 oder -120
        delta = -event.delta / 120 if event.delta else (1 if event.num == 5 else -1)
        
        new_dist = self.camera_distance_var.get() * (1 + delta * 0.1)
        # Zoom-Grenzen einhalten
        self.camera_distance_var.set(max(20, min(1500, new_dist)))
        self._on_camera_param_change()

    def _reset_camera_view(self):
        self._stop_animation() # Stoppt jede aktive Animation
        self.z_rotation_var.set(45)
        self.x_rotation_var.set(60)
        self.cam_x_var.set(0)
        self.cam_y_var.set(0)
        self.camera_distance_var.set(200) # Standard-Distanz
        self.animation_angle = 0.0
        if self.last_scad_code:
            self.img_label.config(bg=self.preview_bg)
            self.update_image_preview(self.last_scad_code)
        else:
            self.img_label.config(image="", text=self.l.get_string("preview_loading"))
            self.img_label.config(image="", text=self.l.get_string("preview_loading"), bg=self.preview_bg)
        self.animate_preview_var.set(False) # Deaktiviert die Animation-Checkbox beim Zurücksetzen

    def update_image_preview(self, scad_code): # Parameter is_animation_frame entfernt
        if not OPENSCAD_EXE or not os.path.exists(OPENSCAD_EXE) or not scad_code:
            print("OpenSCAD executable not found or path is invalid. Cannot render preview.")
            return

        self._stop_animation() # Stoppt immer jede bestehende Animation oder ausstehendes Rendering, bevor ein neues gestartet wird

        # Aktuelle Größe des Labels ermitteln
        w = max(100, self.img_label.winfo_width())
        h = max(100, self.img_label.winfo_height())

        def render():
            temp_scad = os.path.join(os.path.dirname(__file__), "temp_preview.scad")
            temp_png = os.path.join(os.path.dirname(__file__), "temp_preview.png")
            
            # Modell für die Vorschau in ein dezentes Blau-Grau einfärben
            lines = scad_code.splitlines()
            header = [l for l in lines if l.strip().startswith(("use <", "include <"))]
            body = [l for l in lines if not l.strip().startswith(("use <", "include <"))]
            preview_code = "\n".join(header) + "\ncolor([0.4, 0.5, 0.6]) {\n" + "\n".join(body) + "\n}"
            
            with open(temp_scad, "w", encoding="utf-8") as f:
                f.write(preview_code)
            
            self.last_scad_code = scad_code # Speichere den SCAD-Code

            try:
                print(f"Rendering preview for {temp_scad}...")
                result = subprocess.run([
                    OPENSCAD_EXE, "-o", temp_png, 
                    f"--imgsize={w},{h}",
                    # Kamera: translate_x,y,z, rotate_x,y,z, distance
                    f"--camera={self.cam_x_var.get()},{self.cam_y_var.get()},0,{self.x_rotation_var.get()},0,{self.z_rotation_var.get()},{self.camera_distance_var.get()}",
                    temp_scad
                ], check=True, capture_output=True, text=True)
                
                # Print OpenSCAD's stdout and stderr to the console
                if result.stdout:
                    print("OpenSCAD stdout:\n", result.stdout)
                if result.stderr:
                    print("OpenSCAD stderr:\n", result.stderr)

                if os.path.exists(temp_png):
                    self.after(0, lambda path=temp_png: self._show_preview_png(path))
                else:
                    print(f"ERROR: OpenSCAD did not produce a PNG file at {temp_png}")
                    self.after(0, lambda: self.img_label.config(image="", text=self.l.get_string("preview_render_error")))
            except subprocess.CalledProcessError as e:
                print(f"ERROR: OpenSCAD rendering failed with exit code {e.returncode}")
                print("OpenSCAD stdout:\n", e.stdout)
                print("OpenSCAD stderr:\n", e.stderr)
                self.after(0, lambda: self.img_label.config(image="", text=f"{self.l.get_string('rendering_error')} {e.stderr.strip()}"))
            except Exception as e:
                print(f"An unexpected error occurred during rendering: {e}")
                self.after(0, lambda: self.img_label.config(image="", text=f"{self.l.get_string('unexpected_error')} {e}"))
            finally:
                if os.path.exists(temp_scad):
                    os.remove(temp_scad)

                # Wenn die Animation aktiv ist, plane den nächsten Frame, nachdem dieses Rendering abgeschlossen ist
                if self.animate_preview_var.get():
                    self.animation_job_id = self.after(50, self._start_animation)

        self.render_thread = threading.Thread(target=render, daemon=True)
        self.render_thread.start()

    def show_image(self, photo):
        self.img_label.config(image=photo, text="")
        self.img_label.image = photo

    def _show_preview_png(self, path):
        try:
            photo = tk.PhotoImage(file=path)
        except tk.TclError as exc:
            self.img_label.config(image="", text=f"{self.l.get_string('preview_render_error')} {exc}")
            return

        self.show_image(photo)
        try:
            os.remove(path)
        except OSError:
            pass

    def _toggle_animation(self):
        if self.animate_preview_var.get():
            self._start_animation()
        else:
            self._stop_animation()

    def _start_animation(self):
        # Wenn ein Rendering bereits läuft, wird dessen 'finally'-Block den nächsten Animationsframe planen.
        if self.render_thread and self.render_thread.is_alive():
            return

        # Internen Animationswinkel erhöhen
        self.animation_angle = (self.animation_angle + 5.0) % 360
        
        # Aktuellen Tab finden und SCAD-Code mit neuem Winkel generieren
        active_tab = self.notebook.nametowidget(self.notebook.select())
        new_scad = active_tab.build_scad(anim_angle=self.animation_angle)
        
        self.update_image_preview(new_scad) # Dies startet einen neuen Render-Thread

    def _stop_animation(self):
        if self.animation_job_id:
            self.after_cancel(self.animation_job_id)
            self.animation_job_id = None
        # Wir stoppen den render_thread hier nicht explizit, da es sich um einen Unterprozess handelt.
        # Das Abbrechen des nächsten 'after'-Aufrufs beendet jedoch effektiv die Animationsschleife.


if __name__ == "__main__":
    app = GearGUI()
    app.mainloop()
