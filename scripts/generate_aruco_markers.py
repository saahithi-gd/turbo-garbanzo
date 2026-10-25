#!/usr/bin/env python3
"""Regenerate ArUco DICT_4X4_50 door-marker PNGs for astropath_sim.

Uses system OpenCV (/usr/bin/python3). Writes RGB PNGs into:
  ros2_ws/src/astropath_sim/textures/aruco_{id}.png
  ros2_ws/src/astropath_sim/models/aruco_marker_{id}/textures/aruco_{id}.png
  ros2_ws/src/astropath_sim/models/aruco_marker_{id}/materials/textures/aruco_{id}.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import cv2
from cv2 import aruco


def generate(out_root: Path, ids: list[int], size: int, border: int) -> None:
    dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
    textures = out_root / 'textures'
    textures.mkdir(parents=True, exist_ok=True)

    for mid in ids:
        if hasattr(aruco, 'generateImageMarker'):
            img = aruco.generateImageMarker(dictionary, mid, size)
        else:
            img = aruco.drawMarker(dictionary, mid, size)
        bordered = cv2.copyMakeBorder(
            img, border, border, border, border,
            cv2.BORDER_CONSTANT, value=255,
        )
        # Gazebo albedo maps expect RGB, not single-channel.
        # Harmonic PBR albedo on our OBJ meshes does NOT need a V-flip precompensate
        # (verified: camera warp matched the unflipped DICT_4X4_50 pattern).
        rgb = cv2.cvtColor(bordered, cv2.COLOR_GRAY2BGR)

        targets = [
            textures / f'aruco_{mid}.png',
            out_root / 'models' / f'aruco_marker_{mid}' / 'textures' / f'aruco_{mid}.png',
            out_root / 'models' / f'aruco_marker_{mid}' / 'materials' / 'textures' / f'aruco_{mid}.png',
        ]
        for path in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(path), rgb)
            print(f'ID {mid}: {path} ({rgb.shape[1]}x{rgb.shape[0]} RGB)')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--package-root',
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / 'ros2_ws' / 'src' / 'astropath_sim',
        help='Path to astropath_sim package root',
    )
    parser.add_argument('--ids', nargs='+', type=int, default=[0, 1, 2, 3])
    parser.add_argument('--size', type=int, default=400)
    parser.add_argument('--border', type=int, default=40)
    args = parser.parse_args()

    if not args.package_root.is_dir():
        print(f'Package root not found: {args.package_root}', file=sys.stderr)
        return 1

    generate(args.package_root, args.ids, args.size, args.border)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
