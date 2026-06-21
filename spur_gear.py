"""Spur gear SCAD generation functions."""

from gear import generate_header

def scad_spur_gear(params, anim_angle=0):
    """Generate OpenSCAD code for a spur gear.

    Parameters
    ----------
    params: dict
        Dictionary with keys ``modul``, ``zahnzahl``, ``breite``, ``bohrung``,
        ``eingriffswinkel``, ``schraegungswinkel``, ``optimiert`` and optional
        ``profile_shift``.
    anim_angle: float, optional
        Animation rotation angle.
    """
    m = params["modul"]
    z = params["zahnzahl"]
    b = params["breite"]
    d = params["bohrung"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    opt = "true" if params["optimiert"] else "false"
    ps = params.get("profile_shift", 0)

    code = generate_header()
    code += f"rotate([0, 0, {anim_angle}]) spur_gear({m}, {z}, {b}, {d}, {pa}, {ha}, {opt}, {ps});\n"

    if params.get("paar"):
        z2 = params["zahnzahl2"]
        rot2 = (180 / z2) - (anim_angle * (z / z2))
        if params.get("zusammengebaut"):
            dist = m * (z + z2) / 2 + (2 * ps * m)
            code += f"// Achsabstand: {dist}\n"
            code += f"translate([{dist}, 0, 0]) rotate([0, 0, {rot2}]) spur_gear({m}, {z2}, {b}, {d}, {pa}, -{ha}, {opt}, {ps});\n"
        else:
            sep = (m * z / 2) + (m * z2 / 2) + 5
            code += f"translate([{sep}, 0, 0]) rotate([0, 0, {rot2}]) spur_gear({m}, {z2}, {b}, {d}, {pa}, -{ha}, {opt}, {ps});\n"
    return code
