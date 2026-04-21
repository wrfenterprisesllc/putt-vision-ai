# green_reader

Load Scaniverse LiDAR scans of putting greens, pick ball/hole positions
interactively, and visualize a surface-snapped putting line.

**v1** computes a straight line only.  The `LineRenderer.straight_line_path`
method is designed to be replaceable with a physics-based break model later.

## Scaniverse Export

1. Open [Scaniverse](https://scaniverse.com/) on an iPhone/iPad with LiDAR.
2. Scan the putting green — walk slowly around the edges.
3. Tap **Export → OBJ** and transfer the `.obj` file to your machine.

## Install

```bash
pip install -r requirements.txt
```

Dependencies added by this module: `open3d`, `numpy`, `trimesh`, `pytest`.

## Usage

```bash
python -m green_reader path/to/green.obj
```

### CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `--no-align` | off | Skip RANSAC gravity alignment |
| `--triangles N` | 50000 | Target triangle count for simplification |
| `--samples N` | 100 | Points along the putting line |

### Example

```bash
# Load a scan, auto-align gravity, simplify to 30k triangles
python -m green_reader my_green.obj --triangles 30000

# Skip alignment (useful if the scan is already oriented)
python -m green_reader my_green.obj --no-align
```

## Picker Controls

| Action | Key/Mouse |
|--------|-----------|
| Pick a point | Shift + Left-Click |
| Undo last pick | Shift + Right-Click |
| Close window | Q |

Pick the **ball** first, then the **hole**.

## Known Limits (v1)

- **Straight line only** — no break/slope physics yet.
- Gravity alignment assumes a single dominant ground plane.
- Very large scans (>500k triangles) may be slow to load; use `--triangles`
  to reduce.

## Troubleshooting

### Open3D on ARM64 / Raspberry Pi

Open3D wheels may not be available for ARM64 Linux.  Options:

- Build from source: `pip install open3d --no-binary open3d`
- Use an x86 machine or Docker with `--platform linux/amd64`
- Run the green reader on a Mac/PC and transfer the results

### "No display" errors in headless environments

The point picker and renderer require a display (X11/Wayland/macOS).
For headless servers, use X forwarding (`ssh -X`) or a virtual framebuffer
(`xvfb-run`).
