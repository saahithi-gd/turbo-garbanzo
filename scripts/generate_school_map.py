#!/usr/bin/env python3
"""Generate a clean occupancy grid from school_floor SDF wall/clutter geometry.

Option B fallback for Phase 2: the live SLAM map was smeared/ghosted and
unusable for AMCL. This rasterizes known box collisions from model.sdf into
school_floor.{pgm,yaml} plus a PNG preview. SLAM tooling remains for the
portfolio story (run_slam.sh / school_explorer).
"""

from __future__ import annotations

import math
import re
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDF_PATH = ROOT / 'ros2_ws/src/astropath_sim/models/school_floor/model.sdf'
OUT_DIR = ROOT / 'ros2_ws/src/astropath_config/maps'
PREVIEW = ROOT / 'docs/images/school_floor_map.png'

RESOLUTION = 0.05  # m/cell
# School outer walls span ~±7 x ±6; pad so map_server origin is tidy.
ORIGIN_X = -8.0
ORIGIN_Y = -7.5
WIDTH_M = 16.0
HEIGHT_M = 15.0

OCCUPIED = 0
FREE = 254
UNKNOWN = 205


def parse_boxes(sdf_text: str) -> list[tuple[float, float, float, float, float, float]]:
    """Return (cx, cy, yaw, sx, sy, sz) for each link with a box collision."""
    boxes: list[tuple[float, float, float, float, float, float]] = []
    for link in re.finditer(r'<link name=\'([^\']+)\'>(.*?)</link>', sdf_text, re.S):
        body = link.group(2)
        pose_m = re.search(
            r'<pose>([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+'
            r'([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)</pose>',
            body,
        )
        if not pose_m:
            continue
        lx, ly = float(pose_m.group(1)), float(pose_m.group(2))
        lyaw = float(pose_m.group(6))

        coll = re.search(
            r'<collision name=\'collision\'>(.*?)</collision>', body, re.S
        )
        if not coll:
            continue
        cbody = coll.group(1)
        cpose = re.search(
            r'<pose>([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+'
            r'([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)</pose>',
            cbody,
        )
        size_m = re.search(
            r'<box>\s*<size>([-0-9.eE+]+)\s+([-0-9.eE+]+)\s+([-0-9.eE+]+)</size>',
            cbody,
            re.S,
        )
        if not size_m:
            continue
        sx, sy, sz = (float(size_m.group(i)) for i in (1, 2, 3))
        cx_off = cy_off = 0.0
        cyaw = 0.0
        if cpose:
            cx_off, cy_off = float(cpose.group(1)), float(cpose.group(2))
            cyaw = float(cpose.group(6))
        # Collision pose is relative to link; both yaw about Z.
        c, s = math.cos(lyaw), math.sin(lyaw)
        wx = lx + c * cx_off - s * cy_off
        wy = ly + s * cx_off + c * cy_off
        boxes.append((wx, wy, lyaw + cyaw, sx, sy, sz))
    return boxes


def paint_box(
    grid: list[list[int]],
    cx: float,
    cy: float,
    yaw: float,
    sx: float,
    sy: float,
    width: int,
    height: int,
) -> None:
    """Mark cells whose centers fall inside the yawed AABB as occupied."""
    hx, hy = sx / 2.0, sy / 2.0
    c, s = math.cos(yaw), math.sin(yaw)
    # Bounding AABB of rotated rect for iteration bounds
    corners = [(-hx, -hy), (-hx, hy), (hx, -hy), (hx, hy)]
    world = [(cx + c * x - s * y, cy + s * x + c * y) for x, y in corners]
    min_x = min(p[0] for p in world) - RESOLUTION
    max_x = max(p[0] for p in world) + RESOLUTION
    min_y = min(p[1] for p in world) - RESOLUTION
    max_y = max(p[1] for p in world) + RESOLUTION

    i0 = max(0, int((min_x - ORIGIN_X) / RESOLUTION))
    i1 = min(width - 1, int((max_x - ORIGIN_X) / RESOLUTION))
    j0 = max(0, int((min_y - ORIGIN_Y) / RESOLUTION))
    j1 = min(height - 1, int((max_y - ORIGIN_Y) / RESOLUTION))

    for j in range(j0, j1 + 1):
        wy = ORIGIN_Y + (j + 0.5) * RESOLUTION
        for i in range(i0, i1 + 1):
            wx = ORIGIN_X + (i + 0.5) * RESOLUTION
            dx, dy = wx - cx, wy - cy
            lx = c * dx + s * dy
            ly = -s * dx + c * dy
            if abs(lx) <= hx and abs(ly) <= hy:
                grid[j][i] = OCCUPIED


def write_pgm(path: Path, grid: list[list[int]], width: int, height: int) -> None:
    # PGM rows: top of image = max Y (ROS map convention)
    header = f'P5\n{width} {height}\n255\n'.encode('ascii')
    body = bytearray()
    for j in range(height - 1, -1, -1):
        body.extend(struct.pack(f'{width}B', *grid[j]))
    path.write_bytes(header + body)


def write_yaml(path: Path) -> None:
    path.write_text(
        f'image: school_floor.pgm\n'
        f'mode: trinary\n'
        f'resolution: {RESOLUTION:.3f}\n'
        f'origin: [{ORIGIN_X:.3f}, {ORIGIN_Y:.3f}, 0]\n'
        f'negate: 0\n'
        f'occupied_thresh: 0.65\n'
        f'free_thresh: 0.25\n'
    )


def write_preview(path: Path, grid: list[list[int]], width: int, height: int) -> None:
    try:
        from PIL import Image
    except ImportError:
        print(f'[generate_school_map] WARN: Pillow missing; skip preview {path}')
        return
    # Flip vertically to match PGM visual (top = max Y)
    pixels = []
    for j in range(height - 1, -1, -1):
        pixels.extend(grid[j])
    img = Image.new('L', (width, height))
    img.putdata(pixels)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    print(f'[generate_school_map] Wrote preview {path} size={img.size}')


def main() -> None:
    sdf_text = SDF_PATH.read_text()
    boxes = parse_boxes(sdf_text)
    if not boxes:
        raise SystemExit(f'No boxes parsed from {SDF_PATH}')

    width = int(round(WIDTH_M / RESOLUTION))
    height = int(round(HEIGHT_M / RESOLUTION))
    # Start unknown, then free the school interior AABB, then paint obstacles.
    grid = [[UNKNOWN for _ in range(width)] for _ in range(height)]

    # Interior free space (slightly inside outer wall faces at ±7 / ±6)
    free_min_x, free_max_x = -6.90, 6.90
    free_min_y, free_max_y = -5.90, 5.90
    for j in range(height):
        wy = ORIGIN_Y + (j + 0.5) * RESOLUTION
        if wy < free_min_y or wy > free_max_y:
            continue
        for i in range(width):
            wx = ORIGIN_X + (i + 0.5) * RESOLUTION
            if free_min_x <= wx <= free_max_x:
                grid[j][i] = FREE

    for cx, cy, yaw, sx, sy, _sz in boxes:
        paint_box(grid, cx, cy, yaw, sx, sy, width, height)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    pgm = OUT_DIR / 'school_floor.pgm'
    yml = OUT_DIR / 'school_floor.yaml'
    write_pgm(pgm, grid, width, height)
    write_yaml(yml)
    write_preview(PREVIEW, grid, width, height)

    occupied = sum(1 for row in grid for v in row if v == OCCUPIED)
    free = sum(1 for row in grid for v in row if v == FREE)
    print(
        f'[generate_school_map] OK: {pgm.name} {width}x{height} '
        f'boxes={len(boxes)} occupied={occupied} free={free}'
    )
    print(f'[generate_school_map] yaml -> {yml}')


if __name__ == '__main__':
    main()
