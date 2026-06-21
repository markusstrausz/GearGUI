"""Herringbone gear SCAD generation functions."""

from .gear import generate_header

def scad_herringbone_gear(params, anim_angle=0):
    """Generate OpenSCAD code for a herringbone gear.

    Expected ``params`` keys are the same as for ``scad_spur_gear`` plus the
    optional ``profile_shift``.
    """
    m = params["modul"]
    z = params["zahnzahl"]
    b = params["breite"]
    d = params["bohrung"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    ps = params.get("profile_shift", 0)

    code = generate_header()
    code += f"rotate([0, 0, {anim_angle}]) herringbone_gear({m}, {z}, {b}, {d}, {pa}, {ha}, true, {ps});\n"

    if params.get("paar"):
        z2 = params["zahnzahl2"]
        rot2 = (180 / z2) - (anim_angle * (z / z2))
        if params.get("zusammengebaut"):
            dist = m * (z + z2) / 2 + (2 * ps * m)
            code += f"// Achsabstand: {dist}\n"
            code += f"translate([{dist}, 0, 0]) rotate([0, 0, {rot2}]) herringbone_gear({m}, {z2}, {b}, {d}, {pa}, {ha}, true, {ps});\n"
        else:
            sep = (m * z / 2) + (m * z2 / 2) + 5
            code += f"translate([{sep}, 0, 0]) rotate([0, 0, {rot2}]) herringbone_gear({m}, {z2}, {b}, {d}, {pa}, {ha}, true, {ps});\n"
    return code
