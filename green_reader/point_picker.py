"""Interactive ball/hole point selection on a 3D green mesh.

NOTE: This module uses synchronous execution.  Open3D's
``VisualizerWithEditing`` blocks the calling thread and has no async
interface.  Running it inside an asyncio executor adds complexity without
benefit because the visualizer must own the main thread on macOS.
"""

import numpy as np
import open3d as o3d

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SAMPLE_POINTS: int = 100_000
BACKGROUND_COLOR: list[float] = [0.1, 0.1, 0.12]
POINT_SIZE: float = 12.0
GREEN_COLOR: list[float] = [0.4, 0.6, 0.4]
METERS_TO_FEET: float = 3.28084

# ---------------------------------------------------------------------------
# PointPicker
# ---------------------------------------------------------------------------


class PointPicker:
    """Let the user interactively pick two points (ball and hole) on a mesh.

    The mesh is sampled to a dense point cloud before display because
    ``VisualizerWithEditing.get_picked_points()`` returns indices into a
    PointCloud, not a TriangleMesh.

    Args:
        mesh: A processed Open3D triangle mesh (typically from ``MeshLoader``).
    """

    def __init__(self, mesh: o3d.geometry.TriangleMesh) -> None:
        self._mesh = mesh
        self._pcd = mesh.sample_points_uniformly(
            number_of_points=SAMPLE_POINTS,
        )
        self._pcd.paint_uniform_color(GREEN_COLOR)

    def pick(self) -> tuple[np.ndarray, np.ndarray]:
        """Open the picker window and return (ball, hole) as 3D coordinates.

        The user should Shift+Click to pick a point, Shift+RightClick to undo,
        and press Q to close the window.

        Returns:
            Tuple of two (3,) numpy arrays: (ball_position, hole_position).

        Raises:
            RuntimeError: If fewer than two points are picked.
        """
        print("--- Point Picker ---")
        print("  Shift + Left-Click : pick a point")
        print("  Shift + Right-Click: undo last pick")
        print("  Q                  : close window")
        print("Pick the BALL first, then the HOLE.")

        vis = o3d.visualization.VisualizerWithEditing()
        vis.create_window(
            window_name="Pick Ball & Hole",
            width=1280,
            height=800,
        )

        # Render options
        opt = vis.get_render_option()
        opt.background_color = np.array(BACKGROUND_COLOR)
        opt.point_size = POINT_SIZE
        opt.mesh_show_back_face = True

        vis.add_geometry(self._pcd)

        # Set camera looking down at the green centre
        ctr = vis.get_view_control()
        ctr.set_zoom(0.7)
        ctr.set_front([0.0, 0.0, -1.0])
        ctr.set_up([0.0, -1.0, 0.0])
        ctr.set_lookat(np.asarray(self._pcd.get_center()))

        vis.run()  # blocks until window is closed
        vis.destroy_window()

        picked_indices = vis.get_picked_points()
        if len(picked_indices) < 2:
            raise RuntimeError(
                f"Need at least 2 points (ball & hole), got {len(picked_indices)}. "
                "Rerun and Shift+Click on the ball, then the hole."
            )

        points = np.asarray(self._pcd.points)
        ball = points[picked_indices[0]].copy()
        hole = points[picked_indices[1]].copy()

        distance_m = float(np.linalg.norm(hole - ball))
        distance_ft = distance_m * METERS_TO_FEET

        print(f"\nBall: [{ball[0]:.3f}, {ball[1]:.3f}, {ball[2]:.3f}]")
        print(f"Hole: [{hole[0]:.3f}, {hole[1]:.3f}, {hole[2]:.3f}]")
        print(f"Distance: {distance_m:.2f} m ({distance_ft:.1f} ft)")

        return ball, hole
