#!/usr/bin/env python3
"""Replace Gazebo Fuel Ground Plane / Sun includes with inline SDF.

TB3 jazzy worlds pull Ground Plane and Sun from fuel.gazebosim.org. When Fuel
is unreachable (e.g. HTTP 502), gz sim exits and the smoke test cannot run.
This patch is idempotent and re-applied after every vcs import.
"""
from __future__ import annotations

import pathlib
import re
import sys

INLINE = """
    <!-- Astropath Phase 0: local Ground Plane + Sun (Fuel CDN bypass) -->
    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <attenuation>
        <range>1000</range>
        <constant>0.9</constant>
        <linear>0.01</linear>
        <quadratic>0.001</quadratic>
      </attenuation>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <model name="ground_plane">
      <static>true</static>
      <link name="link">
        <collision name="collision">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>100 100</size>
            </plane>
          </geometry>
          <material>
            <ambient>0.8 0.8 0.8 1</ambient>
            <diffuse>0.8 0.8 0.8 1</diffuse>
            <specular>0.8 0.8 0.8 1</specular>
          </material>
        </visual>
      </link>
    </model>
"""

# Match one or both Fuel includes (order may vary; whitespace flexible).
FUEL_BLOCK = re.compile(
    r"\s*<include>\s*"
    r"<uri>https://fuel\.gazebosim\.org/1\.0/OpenRobotics/models/Ground Plane</uri>\s*"
    r"</include>\s*"
    r"<include>\s*"
    r"<uri>https://fuel\.gazebosim\.org/1\.0/OpenRobotics/models/Sun</uri>\s*"
    r"</include>",
    re.MULTILINE,
)

FUEL_GROUND_ONLY = re.compile(
    r"\s*<include>\s*"
    r"<uri>https://fuel\.gazebosim\.org/1\.0/OpenRobotics/models/Ground Plane</uri>\s*"
    r"</include>",
    re.MULTILINE,
)

MARKER = "Astropath Phase 0: local Ground Plane"


def patch_file(path: pathlib.Path) -> str:
    text = path.read_text()
    if MARKER in text:
        return "already-patched"
    if "fuel.gazebosim.org" not in text:
        return "no-fuel"
    new, n = FUEL_BLOCK.subn(INLINE, text, count=1)
    if n == 0:
        new, n = FUEL_GROUND_ONLY.subn(INLINE, text, count=1)
    if n == 0:
        return "unmatched"
    path.write_text(new)
    return "patched"


def main() -> int:
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <turtlebot3_gazebo/worlds dir>", file=sys.stderr)
        return 2
    worlds = pathlib.Path(sys.argv[1])
    if not worlds.is_dir():
        print(f"Missing worlds dir: {worlds}", file=sys.stderr)
        return 1
    rc = 0
    for path in sorted(worlds.glob("*.world")):
        status = patch_file(path)
        print(f"  {path.name}: {status}")
        if status == "unmatched":
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
