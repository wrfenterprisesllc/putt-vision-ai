"""Surface-snapped path computation and 3D rendering.

Uses Open3D's raycasting scene to project paths onto the mesh surface,
then renders the result with ball/hole markers.
"""

import numpy as np
import open3d as o3d

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_SAMPLES: int = 100
RAY_OFFSET: float = 1.0  # metres above z_max for ray origins

# Marker sizes
GOLF_BALL_RADIUS: float = 0.021   # metres (regulation golf ball)
HOLE_RADIUS: float = 0.054        # metres (regulation hole)
LABEL_HEIGHT: float = 0.15        # metres above surface for floating labels
LABEL_RADIUS: float = 0.012       # small floating sphere

# Colours (RGB 0-1)
RED: list[float] = [1.0, 0.2, 0.2]
WHITE: list[float] = [1.0, 1.0, 1.0]
DARK: list[float] = [0.15, 0.15, 0.15]
BALL_LABEL_COLOR: list[float] = [0.2, 0.6, 1.0]   # blue
HOLE_LABEL_COLOR: list[float] = [1.0, 0.8, 0.1]    # gold
GREEN_COLOR: list[float] = [0.4, 0.6, 0.4]
BACKGROUND_COLOR: list[float] = [0.1, 0.1, 0.12]

# ---------------------------------------------------------------------------
# LineRenderer
# ---------------------------------------------------------------------------


class LineRenderer:
    """Compute surface-snapped putting lines and render them in 3D.

    Builds an Open3D raycasting scene from the mesh so paths can be projected
    onto the surface via downward ray casts.

    Args:
        mesh: A processed Open3D triangle mesh (typically from ``MeshLoader``).
    """

    def __init__(self, mesh: o3d.geometry.TriangleMesh) -> None:
        self._mesh = mesh

        mesh_t = o3d.t.geometry.TriangleMesh.from_legacy(mesh)
        self._scene = o3d.t.geometry.RaycastingScene()
        self._scene.add_triangles(mesh_t)

        self._z_max = float(np.asarray(mesh.get_max_bound())[2])

    # ------------------------------------------------------------------
    # Path computation
    # ------------------------------------------------------------------

    def straight_line_path(
        self,
        ball: np.ndarray,
        hole: np.ndarray,
        samples: int = DEFAULT_SAMPLES,
    ) -> np.ndarray:
        """Compute a surface-snapped straight line from ball to hole.

        Interpolates XY linearly and projects each point onto the mesh
        surface by casting downward rays.

        Args:
            ball: (3,) array — ball position.
            hole: (3,) array — hole position.
            samples: Number of points along the path.

        Returns:
            (samples, 3) ndarray of surface-snapped path coordinates.
        """
        t = np.linspace(0.0, 1.0, samples)
        xy = ball[:2][np.newaxis, :] * (1.0 - t[:, np.newaxis]) + \
            hole[:2][np.newaxis, :] * t[:, np.newaxis]

        # Ray origins: above the mesh, pointing straight down
        origin_z = self._z_max + RAY_OFFSET
        origins = np.column_stack([
            xy,
            np.full(samples, origin_z),
        ]).astype(np.float32)

        directions = np.zeros_like(origins)
        directions[:, 2] = -1.0

        rays = np.hstack([origins, directions]).astype(np.float32)
        result = self._scene.cast_rays(o3d.core.Tensor(rays))
        t_hit = result["t_hit"].numpy()

        z_values = origin_z - t_hit

        # Fall back to linear Z interpolation where rays miss
        miss_mask = np.isinf(t_hit)
        if np.any(miss_mask):
            z_linear = ball[2] * (1.0 - t) + hole[2] * t
            z_values[miss_mask] = z_linear[miss_mask]

        path = np.column_stack([xy, z_values])

        # Force exact endpoints
        path[0] = ball
        path[-1] = hole

        return path

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(
        self,
        ball: np.ndarray,
        hole: np.ndarray,
        path: np.ndarray,
    ) -> None:
        """Open a 3D viewer with the mesh, path line, and ball/hole markers.

        Args:
            ball: (3,) array — ball position.
            hole: (3,) array — hole position.
            path: (N, 3) ndarray — the putting line to display.
        """
        geometries: list[o3d.geometry.Geometry3D] = []

        # --- Mesh ---
        mesh_copy = o3d.geometry.TriangleMesh(self._mesh)
        mesh_copy.paint_uniform_color(GREEN_COLOR)
        geometries.append(mesh_copy)

        # --- Path line ---
        n = len(path)
        points = o3d.utility.Vector3dVector(path)
        lines = o3d.utility.Vector2iVector(
            [[i, i + 1] for i in range(n - 1)],
        )
        line_set = o3d.geometry.LineSet(points=points, lines=lines)
        line_set.paint_uniform_color(RED)
        geometries.append(line_set)

        # --- Ball marker (white sphere) ---
        ball_sphere = o3d.geometry.TriangleMesh.create_sphere(
            radius=GOLF_BALL_RADIUS,
        )
        ball_sphere.translate(ball)
        ball_sphere.paint_uniform_color(WHITE)
        ball_sphere.compute_vertex_normals()
        geometries.append(ball_sphere)

        # --- Hole marker (dark sphere) ---
        hole_sphere = o3d.geometry.TriangleMesh.create_sphere(
            radius=HOLE_RADIUS,
        )
        hole_sphere.translate(hole)
        hole_sphere.paint_uniform_color(DARK)
        hole_sphere.compute_vertex_normals()
        geometries.append(hole_sphere)

        # --- Floating label markers ---
        ball_label = o3d.geometry.TriangleMesh.create_sphere(
            radius=LABEL_RADIUS,
        )
        ball_label.translate(ball + np.array([0.0, 0.0, LABEL_HEIGHT]))
        ball_label.paint_uniform_color(BALL_LABEL_COLOR)
        ball_label.compute_vertex_normals()
        geometries.append(ball_label)

        hole_label = o3d.geometry.TriangleMesh.create_sphere(
            radius=LABEL_RADIUS,
        )
        hole_label.translate(hole + np.array([0.0, 0.0, LABEL_HEIGHT]))
        hole_label.paint_uniform_color(HOLE_LABEL_COLOR)
        hole_label.compute_vertex_normals()
        geometries.append(hole_label)

        # --- Coordinate frame ---
        frame = o3d.geometry.TriangleMesh.create_coordinate_frame(size=0.1)
        geometries.append(frame)

        # --- Show ---
        o3d.visualization.draw_geometries(
            geometries,
            window_name="PuttVision — Green Reader",
            width=1280,
            height=800,
            mesh_show_back_face=True,
        )
