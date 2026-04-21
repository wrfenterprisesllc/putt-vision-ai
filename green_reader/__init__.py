"""green_reader — Load Scaniverse LiDAR scans and visualize putting lines.

Loads .obj mesh files exported from Scaniverse, lets the user pick ball and
hole positions interactively, computes a surface-snapped path between them,
and renders the result in 3D.

v1: straight-line path only.  The ``LineRenderer.straight_line_path`` method
is designed to be replaceable with a physics-based break model later.
"""

from green_reader.mesh_loader import MeshLoader
from green_reader.point_picker import PointPicker
from green_reader.line_renderer import LineRenderer

__all__ = ["MeshLoader", "PointPicker", "LineRenderer"]
