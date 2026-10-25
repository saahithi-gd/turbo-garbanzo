#!/usr/bin/env python3
"""Gentle waypoint explorer for school_floor SLAM coverage.

Publishes geometry_msgs/TwistStamped on /cmd_vel (Jazzy TB3 waffle).
Uses modest speeds and pause-at-waypoint to reduce scan-match drift.
"""

from __future__ import annotations

import math
import sys

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data


# Clean corridor-first tour of school_floor (from model.sdf).
# Prefer long straight segments; enter each room once; finish with island loop.
WAYPOINTS: list[tuple[float, float]] = [
    # West corridor → room 0 (NW)
    (-5.5, 1.5),
    (-3.5, 1.5),
    (-3.5, 4.0),
    (-5.0, 4.3),
    (-2.0, 4.3),
    (-3.5, 1.5),
    # North corridor → room 1 (NE) → dead-end spur
    (0.0, 1.5),
    (2.5, 1.5),
    (2.5, 4.0),
    (1.5, 4.3),
    (4.0, 4.3),
    (6.0, 4.3),
    (6.0, 1.5),
    # East corridor → room 3 (SE, narrow door)
    (5.5, 0.0),
    (5.5, -1.5),
    (3.5, -1.5),
    (3.5, -3.8),
    (4.8, -4.3),
    (2.2, -4.3),
    (3.5, -1.5),
    # South corridor → room 2 (SW)
    (0.0, -1.5),
    (-3.5, -1.5),
    (-3.5, -3.8),
    (-5.0, -4.3),
    (-2.0, -4.3),
    (-3.5, -1.5),
    # Full loop around central island (straight legs)
    (-5.5, -1.5),
    (-5.5, 1.5),
    (5.5, 1.5),
    (5.5, -1.5),
    (-5.5, -1.5),
    (-3.5, 1.2),
]


class SchoolExplorer(Node):
    def __init__(self) -> None:
        super().__init__('school_explorer')
        self.declare_parameter('linear_speed', 0.12)
        self.declare_parameter('angular_speed', 0.30)
        self.declare_parameter('goal_tolerance', 0.30)
        self.declare_parameter('yaw_tolerance', 0.18)
        self.declare_parameter('control_rate_hz', 20.0)
        self.declare_parameter('pause_at_waypoint_sec', 1.5)
        self.declare_parameter('loops', 1)

        self._lin = float(self.get_parameter('linear_speed').value)
        self._ang = float(self.get_parameter('angular_speed').value)
        self._tol = float(self.get_parameter('goal_tolerance').value)
        self._yaw_tol = float(self.get_parameter('yaw_tolerance').value)
        self._pause = float(self.get_parameter('pause_at_waypoint_sec').value)
        self._loops = int(self.get_parameter('loops').value)
        rate = float(self.get_parameter('control_rate_hz').value)

        self._pub = self.create_publisher(TwistStamped, 'cmd_vel', 10)
        self._sub = self.create_subscription(
            Odometry, 'odom', self._on_odom, qos_profile_sensor_data
        )
        self._x = 0.0
        self._y = 0.0
        self._yaw = 0.0
        self._have_odom = False
        self._wp_idx = 0
        self._loop_i = 0
        self._done = False
        self._pause_until: float | None = None

        self._timer = self.create_timer(1.0 / rate, self._tick)
        self.get_logger().info(
            f'Explorer ready: {len(WAYPOINTS)} waypoints, '
            f'v={self._lin:.2f} m/s, w={self._ang:.2f} rad/s, '
            f'pause={self._pause:.1f}s, loops={self._loops}'
        )

    def _now(self) -> float:
        return self.get_clock().now().nanoseconds * 1e-9

    def _on_odom(self, msg: Odometry) -> None:
        self._x = msg.pose.pose.position.x
        self._y = msg.pose.pose.position.y
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self._yaw = math.atan2(siny_cosp, cosy_cosp)
        self._have_odom = True

    def _publish(self, vx: float, wz: float) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = vx
        msg.twist.angular.z = wz
        self._pub.publish(msg)

    def _tick(self) -> None:
        if self._done:
            return
        if not self._have_odom:
            return

        if self._pause_until is not None:
            if self._now() < self._pause_until:
                self._publish(0.0, 0.0)
                return
            self._pause_until = None

        if self._wp_idx >= len(WAYPOINTS):
            self._loop_i += 1
            if self._loop_i >= self._loops:
                self._publish(0.0, 0.0)
                self.get_logger().info('EXPLORER_DONE: all waypoints covered')
                self._done = True
                return
            self._wp_idx = 0
            self.get_logger().info(
                f'Starting exploration loop {self._loop_i + 1}/{self._loops}'
            )

        gx, gy = WAYPOINTS[self._wp_idx]
        dx = gx - self._x
        dy = gy - self._y
        dist = math.hypot(dx, dy)
        if dist < self._tol:
            self.get_logger().info(
                f'Reached waypoint {self._wp_idx}: ({gx:.2f}, {gy:.2f}) '
                f'odom=({self._x:.2f}, {self._y:.2f})'
            )
            self._wp_idx += 1
            self._publish(0.0, 0.0)
            if self._pause > 0.0:
                self._pause_until = self._now() + self._pause
            return

        target_yaw = math.atan2(dy, dx)
        yaw_err = math.atan2(
            math.sin(target_yaw - self._yaw), math.cos(target_yaw - self._yaw)
        )

        # Turn in place first (no simultaneous translate+rotate) for cleaner scans
        if abs(yaw_err) > self._yaw_tol:
            wz = self._ang if yaw_err > 0.0 else -self._ang
            self._publish(0.0, wz)
        else:
            self._publish(self._lin, 0.0)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SchoolExplorer()
    try:
        while rclpy.ok() and not node._done:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node._publish(0.0, 0.0)
        node.destroy_node()
        rclpy.shutdown()
    sys.exit(0 if node._done else 1)


if __name__ == '__main__':
    main()
