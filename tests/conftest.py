"""Shared fixtures for green_reader tests.

Generates synthetic putting-green .obj files using trimesh so that tests
can run without real LiDAR scans.  Fixtures are written to
``tests/fixtures/`` and persist between runs for manual CLI testing.
"""

import math
from pathlib import Path

import numpy as np
import pytest
import trimesh

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _ensure_fixtures_dir() -> Path:
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    return FIXTURES_DIR


# ---------------------------------------------------------------------------
# Mesh generators
# ---------------------------------------------------------------------------


def _make_green_mesh(
    nx: int,
    ny: int,
    width: float,
    length: float,
) -> trimesh.Trimesh:
    """Create a rectangular mesh with a gentle sinusoidal surface.

    Surface equation: Z = 0.05 * sin(pi * X / 2) + 0.02 * Y

    Args:
        nx: Grid points along X.
        ny: Grid points along Y.
        width: Extent in X (metres).
        length: Extent in Y (metres).

    Returns:
        A trimesh.Trimesh object.
    """
    xs = np.linspace(0.0, width, nx)
    ys = np.linspace(0.0, length, ny)
    xx, yy = np.meshgrid(xs, ys)
    zz = 0.05 * np.sin(math.pi * xx / 2.0) + 0.02 * yy

    vertices = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])

    # Build triangle indices from the grid
    faces = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            idx = j * nx + i
            # Two triangles per grid cell
            faces.append([idx, idx + 1, idx + nx])
            faces.append([idx + 1, idx + nx + 1, idx + nx])

    return trimesh.Trimesh(
        vertices=vertices,
        faces=np.array(faces),
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def synthetic_green() -> Path:
    """2 m x 3 m green with ~7252 triangles (50x75 grid)."""
    out = _ensure_fixtures_dir() / "sample_green.obj"
    mesh = _make_green_mesh(nx=50, ny=75, width=2.0, length=3.0)
    mesh.export(str(out))
    return out


@pytest.fixture(scope="session")
def dense_green() -> Path:
    """2 m x 3 m green with ~79202 triangles (200x200 grid)."""
    out = _ensure_fixtures_dir() / "dense_green.obj"
    mesh = _make_green_mesh(nx=200, ny=200, width=2.0, length=3.0)
    mesh.export(str(out))
    return out


@pytest.fixture(scope="session")
def empty_obj(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """An .obj file with no geometry — should trigger ValueError."""
    out = tmp_path_factory.mktemp("fixtures") / "empty.obj"
    out.write_text("# empty OBJ\n")
    return out
