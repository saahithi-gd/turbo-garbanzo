#!/usr/bin/env python3
"""Send 5 Nav2 goals through school_floor free space via nav2_simple_commander."""

from __future__ import annotations

import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import rclpy
from geometry_msgs.msg import PoseStamped
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult

# Short corridor goals hugging the central-island walls (reliable free space).
# Prefer ./scripts/run_simple_route.sh (FollowWaypoints) for the demo loop.
GOALS: list[tuple[str, float, float, float]] = [
    ('north_C', 0.0, 1.70, 0.0),
    ('north_E', 3.5, 1.70, -math.pi / 2),
    ('east_S', 3.5, -1.70, math.pi),
    ('south_C', 0.0, -1.70, math.pi),
    ('west_N', -3.5, 1.70, 0.0),
]

SPAWN = (-3.5, 1.70, 0.0)


def _default_log_path() -> Path:
    env = os.environ.get('NAV_GOALS_LOG') or os.environ.get('ASTROPATH_ROOT')
    if env and Path(env).name == 'nav_goals_log.txt':
        return Path(env)
    if os.environ.get('NAV_GOALS_LOG'):
        return Path(os.environ['NAV_GOALS_LOG'])
    if os.environ.get('ASTROPATH_ROOT'):
        return Path(os.environ['ASTROPATH_ROOT']) / 'docs' / 'nav_goals_log.txt'
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / 'scripts' / 'env.sh').is_file():
            return parent / 'docs' / 'nav_goals_log.txt'
    return Path('nav_goals_log.txt')


def pose_xyyaw(navigator: BasicNavigator, x: float, y: float, yaw: float) -> PoseStamped:
    p = PoseStamped()
    p.header.frame_id = 'map'
    p.header.stamp = navigator.get_clock().now().to_msg()
    p.pose.position.x = x
    p.pose.position.y = y
    p.pose.orientation.z = math.sin(yaw / 2.0)
    p.pose.orientation.w = math.cos(yaw / 2.0)
    return p


def main(args=None) -> None:
    log_path = _default_log_path()

    rclpy.init(args=args)
    navigator = BasicNavigator()
    # Seed AMCL first — waitUntilNav2Active blocks until /amcl_pose arrives.
    init = pose_xyyaw(navigator, *SPAWN)
    navigator.setInitialPose(init)
    navigator.get_logger().info(
        f'Set initial pose ({SPAWN[0]}, {SPAWN[1]}); waiting for Nav2…'
    )
    navigator.waitUntilNav2Active()
    time.sleep(1.0)

    lines: list[str] = [
        f'# Astropath Phase 3 nav goals — {datetime.now(timezone.utc).isoformat()}',
        f'# spawn=({SPAWN[0]}, {SPAWN[1]}, yaw={SPAWN[2]})',
        '',
    ]
    successes = 0

    for name, x, y, yaw in GOALS:
        navigator.clearAllCostmaps()
        time.sleep(0.5)
        goal = pose_xyyaw(navigator, x, y, yaw)
        navigator.get_logger().info(f'GOAL_START {name} -> ({x:.2f}, {y:.2f})')
        t0 = time.monotonic()
        navigator.goToPose(goal)
        while not navigator.isTaskComplete():
            time.sleep(0.25)
        result = navigator.getResult()
        dt = time.monotonic() - t0
        ok = result == TaskResult.SUCCEEDED
        # One retry after clearing costmaps (stuck controllers)
        if not ok:
            navigator.get_logger().warn(f'{name} failed ({result.name}); retry once')
            navigator.clearAllCostmaps()
            time.sleep(1.0)
            t0 = time.monotonic()
            navigator.goToPose(goal)
            while not navigator.isTaskComplete():
                time.sleep(0.25)
            result = navigator.getResult()
            dt = time.monotonic() - t0
            ok = result == TaskResult.SUCCEEDED
        status = 'SUCCESS' if ok else f'FAIL({result.name})'
        if ok:
            successes += 1
        line = f'{name}: {status}  xy=({x:.2f},{y:.2f})  dt={dt:.1f}s'
        lines.append(line)
        navigator.get_logger().info(f'GOAL_DONE {line}')

    summary = f'SUMMARY: {successes}/{len(GOALS)} goals succeeded'
    lines.append('')
    lines.append(summary)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text('\n'.join(lines) + '\n')
    navigator.get_logger().info(f'Wrote {log_path}')
    navigator.get_logger().info(summary)

    navigator.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if successes == len(GOALS) else 1)


if __name__ == '__main__':
    main()
