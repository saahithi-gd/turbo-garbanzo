#!/usr/bin/env python3
"""Simple hallway loop around the school_floor central island (Nav2 FollowWaypoints).

Spawn/route stay in corridor *center* (~y=±1.70, x=±3.5) so costmap inflation
does not mark the robot as already in collision (y=1.2 was too close to island).
"""

from __future__ import annotations

import math
import sys
import time

import rclpy
from geometry_msgs.msg import PoseStamped
from lifecycle_msgs.srv import GetState
from nav2_msgs.srv import ManageLifecycleNodes
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from rclpy.parameter import Parameter

# Corridor-center loop (CCW). Clearance from island faces (~±0.97) ≈ 0.73 m.
WAYPOINTS: list[tuple[str, float, float, float]] = [
    ('north_W', -3.5, 1.70, 0.0),
    ('north_C', 0.0, 1.70, 0.0),
    ('north_E', 3.5, 1.70, -math.pi / 2),
    ('east_S', 3.5, -1.70, math.pi),
    ('south_C', 0.0, -1.70, math.pi),
    ('south_W', -3.5, -1.70, math.pi / 2),
    ('west_N', -3.5, 1.70, 0.0),
]

SPAWN = (-3.5, 1.70, 0.0)


def pose_xyyaw(navigator: BasicNavigator, x: float, y: float, yaw: float) -> PoseStamped:
    p = PoseStamped()
    p.header.frame_id = 'map'
    p.header.stamp = navigator.get_clock().now().to_msg()
    p.pose.position.x = x
    p.pose.position.y = y
    p.pose.orientation.z = math.sin(yaw / 2.0)
    p.pose.orientation.w = math.cos(yaw / 2.0)
    return p


def _lifecycle_label(node: BasicNavigator, name: str, timeout: float = 5.0) -> str | None:
    client = node.create_client(GetState, f'{name}/get_state')
    if not client.wait_for_service(timeout_sec=timeout):
        return None
    future = client.call_async(GetState.Request())
    rclpy.spin_until_future_complete(node, future, timeout_sec=timeout)
    if future.result() is None:
        return None
    return future.result().current_state.label


def ensure_nav_active(navigator: BasicNavigator) -> None:
    bt = _lifecycle_label(navigator, 'bt_navigator')
    wp = _lifecycle_label(navigator, 'waypoint_follower')
    navigator.get_logger().info(f'Lifecycle: bt_navigator={bt} waypoint_follower={wp}')
    if bt == 'active' and wp == 'active':
        return
    navigator.get_logger().warn('Nav lifecycle incomplete — RESUME')
    mgr = navigator.create_client(
        ManageLifecycleNodes, 'lifecycle_manager_navigation/manage_nodes'
    )
    if not mgr.wait_for_service(timeout_sec=10.0):
        navigator.get_logger().error('manage_nodes unavailable')
        return
    req = ManageLifecycleNodes.Request()
    req.command = ManageLifecycleNodes.Request.RESUME
    future = mgr.call_async(req)
    rclpy.spin_until_future_complete(navigator, future, timeout_sec=30.0)
    time.sleep(1.0)


def main(args=None) -> None:
    rclpy.init(args=args)
    navigator = BasicNavigator()
    navigator.set_parameters([Parameter('use_sim_time', Parameter.Type.BOOL, True)])

    navigator.get_logger().info('Waiting for /clock…')
    t0 = time.monotonic()
    while rclpy.ok() and navigator.get_clock().now().nanoseconds == 0:
        rclpy.spin_once(navigator, timeout_sec=0.1)
        if time.monotonic() - t0 > 30.0:
            navigator.get_logger().error('No /clock — start ./scripts/run_nav.sh first')
            navigator.destroy_node()
            rclpy.shutdown()
            sys.exit(2)

    ensure_nav_active(navigator)
    navigator.setInitialPose(pose_xyyaw(navigator, *SPAWN))
    navigator.get_logger().info(f'Spawn seed ({SPAWN[0]}, {SPAWN[1]})')

    while not navigator.follow_waypoints_client.wait_for_server(timeout_sec=1.0):
        navigator.get_logger().info('Waiting for follow_waypoints…')
        ensure_nav_active(navigator)

    navigator.waitUntilNav2Active()
    time.sleep(1.0)
    navigator.clearAllCostmaps()
    time.sleep(0.5)

    # Sanity: can we plan to the first distant waypoint?
    start = pose_xyyaw(navigator, *SPAWN)
    probe = pose_xyyaw(navigator, 0.0, 1.70, 0.0)
    path = navigator.getPath(start, probe)
    if path is None or not path.poses:
        navigator.get_logger().error(
            'Planner cannot find a path from spawn — robot may still be in '
            'inflation (restart sim so spawn is y=1.70, or run fix_nav_lifecycle.sh)'
        )
        navigator.destroy_node()
        rclpy.shutdown()
        sys.exit(3)
    navigator.get_logger().info(f'Planner OK ({len(path.poses)} poses to north_C)')

    poses = [pose_xyyaw(navigator, x, y, yaw) for _, x, y, yaw in WAYPOINTS]
    names = [n for n, *_ in WAYPOINTS]
    navigator.get_logger().info(
        'WAYPOINTS: ' + ' -> '.join(f'{n}({x:.1f},{y:.1f})' for n, x, y, _ in WAYPOINTS)
    )

    t_run = time.monotonic()
    navigator.followWaypoints(poses)
    last_wp = -1
    while not navigator.isTaskComplete():
        feedback = navigator.getFeedback()
        if feedback and feedback.current_waypoint != last_wp:
            last_wp = feedback.current_waypoint
            label = names[last_wp] if 0 <= last_wp < len(names) else str(last_wp)
            navigator.get_logger().info(f'Approaching waypoint [{last_wp}] {label}')
        time.sleep(0.25)

    result = navigator.getResult()
    dt = time.monotonic() - t_run
    ok = result == TaskResult.SUCCEEDED
    navigator.get_logger().info(
        f'ROUTE_{"OK" if ok else "FAIL"} result={result.name} dt={dt:.1f}s'
    )
    navigator.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
