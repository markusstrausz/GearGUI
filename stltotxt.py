import numpy as np
import trimesh
import os
import argparse


def extract_boundary_curves(mesh: trimesh.Trimesh):
    """
    Extrahiert Randkanten eines STL-Meshes und gibt geordnete Punktkurven zurück.
    Jede Kurve ist ein (N, 3)-Array.
    """
    edges = mesh.edges_sorted
    edges_unique, counts = np.unique(edges, axis=0, return_counts=True)

    # Randkanten = Kanten, die nur in einem Dreieck vorkommen
    boundary_edges = edges_unique[counts == 1]

    # Graph aus Randkanten
    adjacency = {}
    for a, b in boundary_edges:
        adjacency.setdefault(a, set()).add(b)
        adjacency.setdefault(b, set()).add(a)

    visited = set()
    curves = []

    # Offene Kurven (Startpunkt hat Grad 1)
    for start in adjacency:
        if start in visited:
            continue
        if len(adjacency[start]) != 1:
            continue

        curve = [start]
        visited.add(start)
        prev = None
        current = start

        while True:
            neighbors = adjacency[current] - ({prev} if prev else set())
            if not neighbors:
                break
            nxt = neighbors.pop()
            if nxt in visited:
                break
            curve.append(nxt)
            visited.add(nxt)
            prev, current = current, nxt

        curves.append(np.array(curve))

    # Geschlossene Kurven (alle Knoten Grad 2)
    for start in adjacency:
        if start in visited:
            continue
        if len(adjacency[start]) != 2:
            continue

        loop = [start]
        visited.add(start)
        prev = None
        current = start

        while True:
            neighbors = adjacency[current] - ({prev} if prev else set())
            if not neighbors:
                break
            nxt = neighbors.pop()
            if nxt in visited:
                break
            loop.append(nxt)
            visited.add(nxt)
            prev, current = current, nxt

        curves.append(np.array(loop))

    # Indizes → Koordinaten
    return [mesh.vertices[c] for c in curves]


def save_txt_curves(curves, basename="curve", delimiter=" "):
    """Speichert jede Kurve als TXT-Datei im Format: X Y Z pro Zeile."""
    digits = len(str(len(curves)))
    for i, curve in enumerate(curves, start=1):
        filename = f"{basename}_{i:0{digits}d}.txt"
        np.savetxt(filename, curve, fmt="%.6f", delimiter=delimiter)
        print(f"Gespeichert: {filename}")


def save_dsm_curves(curves, basename="curve", plane="xy", include_z=False):
    """Speichert Kurven im DesignSpark-freundlichen Punktformat.

    Default: eine Zeile pro Punkt als "x;y".
    Optional: "x;y;z" mit include_z=True.
    """
    plane_axes = {
        "xy": (0, 1),
        "xz": (0, 2),
        "yz": (1, 2),
    }
    ax0, ax1 = plane_axes[plane]

    digits = len(str(len(curves)))
    for i, curve in enumerate(curves, start=1):
        filename = f"{basename}_{i:0{digits}d}.txt"
        with open(filename, "w", encoding="utf-8") as out:
            for p in curve:
                if include_z:
                    out.write(f"{p[0]:.6f};{p[1]:.6f};{p[2]:.6f}\n")
                else:
                    out.write(f"{p[ax0]:.6f};{p[ax1]:.6f}\n")
        print(f"Gespeichert: {filename}")


def stl_to_txt(stl_path, mode="xyz", plane="xy", separator="space"):
    print(f"Lade STL: {stl_path}")
    mesh = trimesh.load_mesh(stl_path, process=True)

    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(mesh.dump())

    print("Extrahiere Randkurven…")
    curves = extract_boundary_curves(mesh)
    print(f"Gefundene Kurven: {len(curves)}")

    if not curves and mesh.is_watertight:
        print("Hinweis: Das STL ist wasserdicht/geschlossen und hat daher keine Randkanten.")
        print("Dieses Skript exportiert Randkurven, nicht Silhouetten oder Schnitte.")
        return

    base, _ = os.path.splitext(stl_path)
    if mode == "xyz":
        delimiter = " " if separator == "space" else ","
        save_txt_curves(curves, basename=base, delimiter=delimiter)
    elif mode == "dsm2d":
        save_dsm_curves(curves, basename=base, plane=plane, include_z=False)
    elif mode == "dsm3d":
        save_dsm_curves(curves, basename=base, plane=plane, include_z=True)
    else:
        raise ValueError(f"Unbekannter Modus: {mode}")

    print("Fertig.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extrahiert Randkurven aus STL und speichert Punktdateien."
    )
    parser.add_argument("stl", help="Pfad zur STL-Datei")
    parser.add_argument(
        "--mode",
        choices=["xyz", "dsm2d", "dsm3d"],
        default="xyz",
        help="Ausgabeformat: xyz (x y z), dsm2d (x;y), dsm3d (x;y;z)",
    )
    parser.add_argument(
        "--separator",
        choices=["space", "comma"],
        default="space",
        help="Nur fuer --mode xyz: Trennzeichen zwischen X/Y/Z.",
    )
    parser.add_argument(
        "--plane",
        choices=["xy", "xz", "yz"],
        default="xy",
        help="Projektionsebene fuer dsm2d (Default: xy)",
    )
    args = parser.parse_args()

    stl_to_txt(args.stl, mode=args.mode, plane=args.plane, separator=args.separator)
