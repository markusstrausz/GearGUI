"""Rack gear SCAD generation function."""

from .gear import generate_header

def scad_rack(params, anim_angle=0):
    """Generate OpenSCAD code for a rack.

    Expected ``params`` keys: ``modul``, ``laenge``, ``hoehe``, ``breite``,
    ``eingriffswinkel`` and ``schraegungswinkel``.
    """
    m = params["modul"]
    L = params["laenge"]
    H = params["hoehe"]
    W = params["breite"]
    pa = params["eingriffswinkel"]
    ha = params["schraegungswinkel"]
    shift = (anim_angle / 360.0) * (math.pi * m * 20)
    return (
        generate_header()
        + f"translate([{-shift % (math.pi * m)}, 0, 0]) rack({m}, {L}, {H}, {W}, {pa}, {ha});\n"
    )
