#!/usr/bin/env python3
"""Publish /initialpose a few times for AMCL (school_floor spawn)."""

from __future__ import annotations

import math

import rclpy
from geometry_msgs.msg import PoseWithCovarianceStamped
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy


class SetInitialPose(Node):
    def __init__(self) -> None:
        super().__init__('set_initial_pose')
        self.declare_parameter('x', -3.5)
        self.declare_parameter('y', 1.70)
        self.declare_parameter('yaw', 0.0)
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('publish_count', 5)
        self.declare_parameter('publish_period', 0.5)

        self._x = float(self.get_parameter('x').value)
        self._y = float(self.get_parameter('y').value)
        self._yaw = float(self.get_parameter('yaw').value)
        self._frame = str(self.get_parameter('frame_id').value)
        self._left = int(self.get_parameter('publish_count').value)
        period = float(self.get_parameter('publish_period').value)

        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
        )
        self._pub = self.create_publisher(PoseWithCovarianceStamped, 'initialpose', qos)
        self._timer = self.create_timer(period, self._tick)
        self.get_logger().info(
            f'Publishing initial pose ({self._x:.2f}, {self._y:.2f}, yaw={self._yaw:.2f})'
        )

    def _tick(self) -> None:
        if self._left <= 0:
            self._timer.cancel()
            return
        msg = PoseWithCovarianceStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = self._frame
        msg.pose.pose.position.x = self._x
        msg.pose.pose.position.y = self._y
        msg.pose.pose.orientation.z = math.sin(self._yaw / 2.0)
        msg.pose.pose.orientation.w = math.cos(self._yaw / 2.0)
        # Modest covariance so AMCL accepts the seed
        msg.pose.covariance[0] = 0.25
        msg.pose.covariance[7] = 0.25
        msg.pose.covariance[35] = 0.07
        self._pub.publish(msg)
        self._left -= 1
        if self._left == 0:
            self.get_logger().info('INITIAL_POSE_DONE')


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SetInitialPose()
    try:
        while rclpy.ok() and node._left > 0:
            rclpy.spin_once(node, timeout_sec=0.2)
        # brief settle
        for _ in range(5):
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
