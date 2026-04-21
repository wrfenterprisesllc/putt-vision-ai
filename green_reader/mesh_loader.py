"""Mesh loading, cleaning, simplification, and gravity alignment.

Accepts Scaniverse .obj exports and prepares them for interactive picking
and line rendering.
"""

from pathlib import Path
from typing import Union

import numpy as np
import open3d as o3d

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TARGET_TRIANGLES: int = 50_000
RANSAC_SAMPLE_POINTS: int = 10_000
GREEN_COLOR: list[float] = [0.4, 0.6, 0.4]

# ---------------------------------------------------------------------------
# MeshLoader
# ---------------------------------------------------------------------------


class MeshLoader:
    """Load, clean, simplify, and optionally gravity-align a triangle mesh.

    All processing happens eagerly in the constructor so the resulting mesh
    is ready for downstream use immediately.

    Args:
        path: Path to an .obj (or any Open3D-supported mesh) file.
        target_triangles: Maximum triangle count after simplification.
            Meshes with fewer triangles are left untouched.
        align_gravity: If True, attempt RANSAC ground-plane detection and
            rotate the mesh so the ground normal aligns with +Z.
    """

    def __init__(
        self,
        path: Union[str, Path],
        target_triangles: int = DEFAULT_TARGET_TRIANGLES,
        align_gravity: bool = True,
    ) -> None:
        self._path = Path(path)
        if not self._path.exists():
            raise FileNotFoundError(f"Mesh file not found: {self._path}")

        # --- Load ---
        self._mesh = o3d.io.read_triangle_mesh(str(self._path))
        if len(self._mesh.vertices) == 0:
            raise ValueError(f"Mesh has no vertices: {self._path}")

        self._original_triangles = len(self._mesh.triangles)

        # --- Clean ---
        self._mesh.remove_degenerate_triangles()
        self._mesh.remove_duplicated_triangles()
        self._mesh.remove_duplicated_vertices()
        self._mesh.remove_non_manifold_edges()

        # --- Simplify ---
        if len(self._mesh.triangles) > target_triangles:
            self._mesh = self._mesh.simplify_quadric_decimation(
                target_number_of_triangles=target_triangles,
            )

        # --- Normals ---
        self._mesh.compute_vertex_normals()

        # --- Gravity alignment ---
        if align_gravity:
            self._align_to_gravity()

        # --- Colour ---
        self._mesh.paint_uniform_color(GREEN_COLOR)

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @property
    def mesh(self) -> o3d.geometry.TriangleMesh:
        """The processed Open3D triangle mesh."""
        return self._mesh

    def get_bounds(self) -> tuple[np.ndarray, np.ndarray]:
        """Axis-aligned bounding box as (min_bound, max_bound)."""
        return (
            np.asarray(self._mesh.get_min_bound()),
            np.asarray(self._mesh.get_max_bound()),
        )

    def stats(self) -> dict:
        """Summary statistics for the loaded mesh.

        Returns:
            Dict with keys: file, vertices, triangles, original_triangles,
            size_m (bounding-box dimensions), watertight.
        """
        min_b, max_b = self.get_bounds()
        size = max_b - min_b
        return {
            "file": str(self._path),
            "vertices": len(self._mesh.vertices),
            "triangles": len(self._mesh.triangles),
            "original_triangles": self._original_triangles,
            "size_m": size,
            "watertight": self._mesh.is_watertight(),
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _align_to_gravity(self) -> None:
        """Rotate the mesh so the dominant ground plane faces +Z.

        Uses RANSAC plane segmentation on a sampled point cloud.  Falls back
        silently (with a warning) if plane detection fails.
        """
        try:
            pcd = self._mesh.sample_points_uniformly(
                number_of_points=RANSAC_SAMPLE_POINTS,
            )
            plane_model, _inliers = pcd.segment_plane(
                distance_threshold=0.01,
                ransac_n=3,
                num_iterations=1000,
            )
            # plane_model: [a, b, c, d] where ax + by + cz + d = 0
            normal = np.array(plane_model[:3], dtype=np.float64)
            normal /= np.linalg.norm(normal)

            # Flip normal so it roughly points up (+Z)
            if normal[2] < 0:
                normal = -normal

            target = np.array([0.0, 0.0, 1.0])
            self._mesh.rotate(
                _rotation_align(normal, target),
                center=self._mesh.get_center(),
            )
        except RuntimeError as exc:
            print(f"Warning: gravity alignment failed ({exc}), continuing unaligned")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rotation_align(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Compute 3x3 rotation matrix aligning *source* direction to *target*.

    Uses the Rodrigues rotation formula.  Returns the identity matrix when
    the vectors are already aligned (or anti-aligned with a 180-degree flip).
    """
    v = np.cross(source, target)
    c = float(np.dot(source, target))

    # Already aligned
    if np.linalg.norm(v) < 1e-8:
        if c > 0:
            return np.eye(3)
        # 180-degree flip — rotate around any perpendicular axis
        perp = np.array([1.0, 0.0, 0.0])
        if abs(np.dot(source, perp)) > 0.9:
            perp = np.array([0.0, 1.0, 0.0])
        perp = np.cross(source, perp)
        perp /= np.linalg.norm(perp)
        # 180-degree rotation around perp: R = 2 * outer(perp, perp) - I
        return 2.0 * np.outer(perp, perp) - np.eye(3)

    skew = np.array([
        [0.0, -v[2], v[1]],
        [v[2], 0.0, -v[0]],
        [-v[1], v[0], 0.0],
    ])
    return np.eye(3) + skew + skew @ skew / (1.0 + c)
