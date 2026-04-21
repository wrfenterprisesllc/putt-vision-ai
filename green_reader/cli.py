"""Command-line interface for the green reader.

Usage::

    python -m green_reader path/to/green.obj [--no-align] [--triangles N] [--samples N]
"""

import argparse

import numpy as np

from green_reader.mesh_loader import MeshLoader
from green_reader.point_picker import PointPicker
from green_reader.line_renderer import LineRenderer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METERS_TO_FEET: float = 3.28084

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    """Parse arguments, load mesh, pick points, compute path, and render."""
    parser = argparse.ArgumentParser(
        prog="green_reader",
        description="Load a LiDAR green scan and visualize a putting line.",
    )
    parser.add_argument(
        "obj_path",
        help="Path to an .obj mesh file (e.g. Scaniverse export).",
    )
    parser.add_argument(
        "--no-align",
        action="store_true",
        help="Skip gravity alignment (RANSAC ground-plane rotation).",
    )
    parser.add_argument(
        "--triangles",
        type=int,
        default=50_000,
        help="Target triangle count for mesh simplification (default: 50000).",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=100,
        help="Number of sample points along the putting line (default: 100).",
    )
    args = parser.parse_args()

    # --- Load ---
    print(f"Loading mesh: {args.obj_path}")
    loader = MeshLoader(
        args.obj_path,
        target_triangles=args.triangles,
        align_gravity=not args.no_align,
    )
    stats = loader.stats()
    print(f"  Vertices : {stats['vertices']:,}")
    print(f"  Triangles: {stats['triangles']:,} (was {stats['original_triangles']:,})")
    print(f"  Size     : {stats['size_m'][0]:.2f} x {stats['size_m'][1]:.2f} x {stats['size_m'][2]:.2f} m")
    print(f"  Watertight: {stats['watertight']}")

    # --- Pick ---
    picker = PointPicker(loader.mesh)
    ball, hole = picker.pick()

    # --- Compute path ---
    renderer = LineRenderer(loader.mesh)
    path = renderer.straight_line_path(ball, hole, samples=args.samples)

    # --- Summary ---
    distance_m = float(np.linalg.norm(hole - ball))
    distance_ft = distance_m * METERS_TO_FEET
    z_range_cm = float(np.ptp(path[:, 2])) * 100.0
    print(
        f"\nPutt distance: {distance_m:.2f} m ({distance_ft:.1f} ft) | "
        f"Samples: {args.samples} | "
        f"Max elevation change: {z_range_cm:.1f} cm"
    )

    # --- Render ---
    renderer.render(ball, hole, path)
