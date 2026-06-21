"""Reusable gear math helpers for UI and tests."""

from __future__ import annotations

import math


def spur_pair_axis_distance(module: float, z1: int, z2: int, profile_shift: float = 0.0) -> float:
    return module * (z1 + z2) / 2.0 + (2.0 * profile_shift * module)


def herringbone_pair_axis_distance(module: float, z1: int, z2: int, profile_shift: float = 0.0) -> float:
    return spur_pair_axis_distance(module, z1, z2, profile_shift)


def rack_pinion_axis_distance(module: float, pinion_teeth: int) -> float:
    return module * pinion_teeth / 2.0


def rack_pinion_motion(module: float, pinion_teeth: int, anim_angle: float) -> float:
    return (anim_angle / 360.0) * (math.pi * module * pinion_teeth)


def worm_axis_distance(module: float, thread_starts: int, lead_angle_deg: float, gear_teeth: int) -> float:
    lead_rad = math.radians(lead_angle_deg)
    if lead_rad <= 0 or math.sin(lead_rad) == 0:
        raise ValueError("lead_angle_deg must be > 0")
    worm_radius = (module * thread_starts) / (2.0 * math.sin(lead_rad))
    gear_radius = (module * gear_teeth) / 2.0
    return worm_radius + gear_radius


def worm_root_diameter(module: float, thread_starts: int, lead_angle_deg: float) -> float:
    lead_rad = math.radians(lead_angle_deg)
    if lead_rad <= 0 or math.sin(lead_rad) == 0:
        raise ValueError("lead_angle_deg must be > 0")
    worm_radius = (module * thread_starts) / (2.0 * math.sin(lead_rad))
    clearance = module / 6.0
    root_radius = worm_radius - module - clearance
    return max(0.0, 2.0 * root_radius)


def ring_inner_axis_distance(module: float, ring_teeth: int, inner_teeth: int) -> float:
    if inner_teeth <= 0 or inner_teeth >= ring_teeth:
        raise ValueError("inner_teeth must be > 0 and < ring_teeth")
    return module * (ring_teeth - inner_teeth) / 2.0


def planetary_ring_teeth(sun_teeth: int, planet_teeth: int) -> int:
    return sun_teeth + 2 * planet_teeth


def planetary_planet_center_distance(module: float, sun_teeth: int, planet_teeth: int) -> float:
    return module * (sun_teeth + planet_teeth) / 2.0
