import math
from .gear import generate_header

def scad_worm_gear(params, anim_angle=0):
    """
    SCAD-Code für Schnecke + Wurmrad mit Achsabstand aus den bereits
    berechneten Parametern (z.B. 'achsabstand' im UI).
    """

    m  = params["modul"]
    z  = params["zahnzahl"]
    ts = params["thread_starts"]
    w  = params["breite"]
    l  = params["laenge_schnecke"]
    wb = params["bohrung_schnecke"]
    gb = params["bohrung"]
    pa = params["eingriffswinkel"]
    la = params["steigungswinkel"]
    opt = "true" if params.get("optimiert", True) else "false"
    assembled = params.get("zusammengebaut", True)

    # 👉 WICHTIG: Achsabstand NICHT selbst berechnen, sondern den Wert verwenden,
    # den das UI bereits ermittelt hat. Zusätzlich wird die Position des
    # Wurmrades leicht seitlich versetzt, damit die Schnecke innerhalb des
    # Wurmrades liegt. Dafür benötigen wir den Durchmesser der Schnecke (d_worm).
    if "achsabstand" not in params:
        raise KeyError("Parameter 'achsabstand' fehlt – bitte berechne ihn im UI und übergebe ihn.")
    # Basis-Achsabstand aus den Parametern
    axis = params["achsabstand"]

    # Berechne den Durchmesser der Schnecke, um die korrekte x‑Position zu
    # bestimmen, sodass die Schnecke im Inneren des Wurmrades liegt.
    gamma = math.radians(la)
    # r_worm = m * ts / (2 * sin(lead_angle))
    d_worm = 2 * m * ts / math.sin(gamma)

    # No additional offsets are applied; the gear is positioned solely based on
    # the calculated axis and worm diameter to keep the worm centered inside the gear.
    y_offset = -d_worm / 2
    z_offset = -d_worm / 2

    # auseinanderziehen, wenn nicht zusammengebaut
    if not assembled:
        axis += 15

    # Berechne die endgültige X‑Position des Wurmrades nach dem eventuellen
    # Auseinanderziehen. Der Mittelpunkt wird um die Hälfte des Schneckendurchmessers
    # nach innen verschoben, sodass die Schnecke im Inneren liegt.
    gear_x = axis - d_worm / 2

    # Animation: Rad dreht ts/z mal schneller
    rot_gear = -anim_angle * ts / z

    code = generate_header()

    # Schnecke – exakt wie im UI: rotate([90, 0, 0]) bei anim_angle=0
    code += "// Schnecke\n"
    code += (
        f"rotate([90, 0, {anim_angle}]) "
        f"worm({m}, {ts}, {l}, {wb}, {pa}, {la}, {str(assembled).lower()});\n"
    )

    # Wurmrad – exakt auf Achsabstand
    code += "// Wurmrad\n"
    code += (
        f"translate([{gear_x}, {y_offset}, {z_offset}]) "
        f"rotate([0, 0, {rot_gear}]) "
        f"worm_gear({m}, {z}, {ts}, {w}, {l}, {gb}, {pa}, {la}, {opt}, false, 0.1, 0);\n"
    )

    return code
