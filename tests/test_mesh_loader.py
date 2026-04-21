"""Tests for green_reader.mesh_loader.MeshLoader."""

from pathlib import Path

import numpy as np
import pytest

from green_reader.mesh_loader import MeshLoader


class TestMeshLoaderBasic:
    """Basic loading and property tests."""

    def test_loads_synthetic_green(self, synthetic_green: Path) -> None:
        loader = MeshLoader(synthetic_green, align_gravity=False)
        assert len(loader.mesh.vertices) > 0
        assert len(loader.mesh.triangles) > 0
        assert loader.mesh.has_vertex_normals()

    def test_stats_keys(self, synthetic_green: Path) -> None:
        loader = MeshLoader(synthetic_green, align_gravity=False)
        s = loader.stats()
        expected_keys = {
            "file", "vertices", "triangles", "original_triangles",
            "size_m", "watertight",
        }
        assert set(s.keys()) == expected_keys

    def test_bounds_shape(self, synthetic_green: Path) -> None:
        loader = MeshLoader(synthetic_green, align_gravity=False)
        min_b, max_b = loader.get_bounds()
        assert min_b.shape == (3,)
        assert max_b.shape == (3,)
        assert np.all(max_b >= min_b)


class TestSimplification:
    """Quadric decimation reduces triangle count."""

    def test_dense_mesh_simplified(self, dense_green: Path) -> None:
        target = 10_000
        loader = MeshLoader(
            dense_green,
            target_triangles=target,
            align_gravity=False,
        )
        assert len(loader.mesh.triangles) <= target
        assert loader.stats()["original_triangles"] > target

    def test_small_mesh_not_simplified(self, synthetic_green: Path) -> None:
        """Meshes already under the target should not be changed."""
        loader = MeshLoader(
            synthetic_green,
            target_triangles=100_000,
            align_gravity=False,
        )
        assert loader.stats()["triangles"] == loader.stats()["original_triangles"]


class TestGravityAlignment:
    """RANSAC ground-plane alignment rotates Z to thinnest extent."""

    def test_z_is_thinnest_after_alignment(self, synthetic_green: Path) -> None:
        loader = MeshLoader(synthetic_green, align_gravity=True)
        min_b, max_b = loader.get_bounds()
        extents = max_b - min_b
        # Z should be the smallest dimension after aligning a mostly-flat green
        assert np.argmin(extents) == 2, (
            f"Expected Z to be thinnest, got extents {extents}"
        )


class TestErrorHandling:
    """Validation errors on bad inputs."""

    def test_missing_file_raises(self) -> None:
        with pytest.raises(FileNotFoundError):
            MeshLoader("/nonexistent/path.obj")

    def test_empty_obj_raises(self, empty_obj: Path) -> None:
        with pytest.raises(ValueError, match="no vertices"):
            MeshLoader(empty_obj)
