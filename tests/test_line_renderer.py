"""Tests for green_reader.line_renderer.LineRenderer."""

import math
from pathlib import Path

import numpy as np
import pytest

from green_reader.line_renderer import LineRenderer
from green_reader.mesh_loader import MeshLoader


@pytest.fixture(scope="module")
def renderer(synthetic_green: Path) -> LineRenderer:
    """LineRenderer built from the synthetic green fixture."""
    loader = MeshLoader(synthetic_green, align_gravity=False)
    return LineRenderer(loader.mesh)


# Ball near one end, hole near the other — straight Y-axis putt
BALL = np.array([1.0, 0.5, 0.0])
HOLE = np.array([1.0, 2.5, 0.0])


class TestStraightLinePath:
    """Surface-snapped straight-line path computation."""

    def test_path_shape(self, renderer: LineRenderer) -> None:
        path = renderer.straight_line_path(BALL, HOLE, samples=80)
        assert path.shape == (80, 3)

    def test_endpoints_exact(self, renderer: LineRenderer) -> None:
        path = renderer.straight_line_path(BALL, HOLE, samples=50)
        np.testing.assert_array_equal(path[0], BALL)
        np.testing.assert_array_equal(path[-1], HOLE)

    def test_z_near_analytic_surface(self, renderer: LineRenderer) -> None:
        """Interior Z values should be close to Z = 0.05*sin(pi*X/2) + 0.02*Y."""
        path = renderer.straight_line_path(BALL, HOLE, samples=100)
        # Skip first and last (forced endpoints) — check interior
        for pt in path[1:-1]:
            expected_z = 0.05 * math.sin(math.pi * pt[0] / 2.0) + 0.02 * pt[1]
            assert abs(pt[2] - expected_z) < 0.02, (
                f"Z={pt[2]:.4f} too far from analytic {expected_z:.4f} at "
                f"({pt[0]:.3f}, {pt[1]:.3f})"
            )

    def test_y_monotonic_for_straight_putt(self, renderer: LineRenderer) -> None:
        """For a straight Y-axis putt, Y values should increase monotonically."""
        path = renderer.straight_line_path(BALL, HOLE, samples=100)
        y_vals = path[:, 1]
        assert np.all(np.diff(y_vals) >= 0), "Y should be monotonically increasing"

    def test_default_samples(self, renderer: LineRenderer) -> None:
        """Default sample count should be 100."""
        path = renderer.straight_line_path(BALL, HOLE)
        assert path.shape[0] == 100
