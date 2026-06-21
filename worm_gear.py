"""Worm gear (single worm) SCAD generation function."""

from .gear import generate_header

def scad_worm(params, anim_angle=0):
    """Generate OpenSCAD code for a single worm.

    Expected ``params`` keys: ``modul``, ``zahnzahl``, ``breite``, ``bohrung``,
    ``eingriffswinkel``, ``schraegungswinkel``.
    """
    m = params["modul"]
    ts = params["zahnzahl"]
    l = params["breite"]
    d = params["bohrung"]
    pa = params["eingriffswinkel"]
    la = params["schraegungswinkel"]
    tb = "true" if params.get("zusammengebaut", True) else "false"
    # Tilt the worm by 90° around the X‑axis when assembled to show the correct orientation
    tilt = "90, " if params.get("zusammengebaut", True) else ""
    return (
        generate_header()
        + f"rotate([{tilt}{anim_angle}, 0, 0]) worm({m}, {ts}, {l}, {d}, {pa}, {la}, {tb});\n"
    )
