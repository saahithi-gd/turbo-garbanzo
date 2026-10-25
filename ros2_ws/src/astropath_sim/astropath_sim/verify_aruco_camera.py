#!/usr/bin/env python3
"""Capture /camera/image_raw, detect ArUco DICT_4X4_50, save evidence PNG.

Faces door marker 0 via TwistStamped on /cmd_vel (Jazzy TB3), captures a
frame, then runs OpenCV ArUco detection in a subprocess (avoids a known
segfault when cv2.aruco runs in-process alongside rclpy on this stack).
"""
from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import cv2
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image


def _repo_root() -> Path:
    env = os.environ.get('ASTROPATH_ROOT')
    if env:
        p = Path(env).resolve()
        if (p / 'docs').is_dir():
            return p
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / 'docs' / 'DECISIONS.md').is_file():
            return parent
    return Path.cwd()


class ArucoVerifier(Node):
    def __init__(self) -> None:
        super().__init__('verify_aruco_camera')
        self.bridge = CvBridge()
        self.latest = None
        self.yaw: float | None = None
        self.create_subscription(
            Image, '/camera/image_raw', self._on_image, qos_profile_sensor_data,
        )
        self.create_subscription(
            Odometry, '/odom', self._on_odom, qos_profile_sensor_data,
        )
        self.cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)

    def _on_image(self, msg: Image) -> None:
        self.latest = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

    def _on_odom(self, msg: Odometry) -> None:
        q = msg.pose.pose.orientation
        siny_cosp = 2.0 * (q.w * q.z + q.x * q.y)
        cosy_cosp = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
        self.yaw = math.atan2(siny_cosp, cosy_cosp)

    def spin_until(self, predicate, timeout_s: float, label: str) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)
            if predicate():
                return
        raise TimeoutError(f'Timeout waiting for {label} ({timeout_s:.0f}s)')

    def wait_for_image(self, timeout_s: float):
        self.spin_until(lambda: self.latest is not None, timeout_s, '/camera/image_raw')
        return self.latest

    def publish_cmd(self, linear_x: float = 0.0, angular_z: float = 0.0) -> None:
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist = Twist()
        msg.twist.linear.x = linear_x
        msg.twist.angular.z = angular_z
        self.cmd_pub.publish(msg)

    def face_yaw(self, target_yaw: float, speed: float = 0.5, tol: float = 0.08) -> None:
        self.spin_until(lambda: self.yaw is not None, 30.0, '/odom yaw')
        deadline = time.time() + 20.0
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.05)
            assert self.yaw is not None
            err = math.atan2(math.sin(target_yaw - self.yaw), math.cos(target_yaw - self.yaw))
            if abs(err) < tol:
                break
            self.publish_cmd(angular_z=max(-speed, min(speed, 1.5 * err)))
            time.sleep(0.05)
        self.publish_cmd()
        time.sleep(0.4)


def try_set_pose_gz(x: float, y: float, yaw: float) -> bool:
    cmd = [
        'gz', 'service', '-s', '/world/school_floor/set_pose',
        '--reqtype', 'gz.msgs.Pose',
        '--reptype', 'gz.msgs.Boolean',
        '--timeout', '2000',
        '--req',
        f'name: "waffle", position: {{x: {x}, y: {y}, z: 0.01}}, '
        f'orientation: {{z: {math.sin(yaw / 2):.6f}, w: {math.cos(yaw / 2):.6f}}}',
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        ok = r.returncode == 0 and 'true' in (r.stdout + r.stderr).lower()
        print(f'gz set_pose {"OK" if ok else "soft-fail"} → ({x}, {y}, yaw={yaw:.2f})')
        return ok
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        print(f'gz set_pose unavailable: {exc}')
        return False


_DETECT_SCRIPT = r'''
import sys
import cv2
import numpy as np
from cv2 import aruco

img_path, out_path = sys.argv[1], sys.argv[2]
img = cv2.imread(img_path)
if img is None:
    print("DETECT_FAIL=read")
    sys.exit(3)
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
lo, hi = np.percentile(gray, [5, 95])
stretched = gray
if hi > lo:
    stretched = np.clip((gray.astype(np.float32) - lo) * 255.0 / (hi - lo), 0, 255).astype(np.uint8)
dictionary = aruco.getPredefinedDictionary(aruco.DICT_4X4_50)
if hasattr(aruco, "DetectorParameters_create"):
    params = aruco.DetectorParameters_create()
else:
    params = aruco.DetectorParameters()
params.minMarkerPerimeterRate = 0.01
params.adaptiveThreshWinSizeMax = 53

detected = []
vis = img
for candidate, flipped in (
    (stretched, False),
    (gray, False),
    (cv2.flip(stretched, 0), True),
    (cv2.flip(gray, 0), True),
):
    corners, ids, _ = aruco.detectMarkers(candidate, dictionary, parameters=params)
    if ids is None:
        continue
    detected = sorted({int(i) for i in ids.flatten()})
    vis = cv2.cvtColor(candidate, cv2.COLOR_GRAY2BGR) if flipped else img.copy()
    aruco.drawDetectedMarkers(vis, corners, ids)
    break

cv2.putText(
    vis,
    f"DICT_4X4_50 IDs: {detected if detected else 'none'}",
    (10, 30),
    cv2.FONT_HERSHEY_SIMPLEX,
    0.7,
    (0, 220, 0),
    2,
    cv2.LINE_AA,
)
cv2.imwrite(out_path, vis)
print(f"DETECTED_IDS={detected}")
sys.exit(0 if detected else 2)
'''


def detect_in_subprocess(bgr, out_path: Path) -> list[int]:
    with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
        raw_path = Path(tmp.name)
    try:
        cv2.imwrite(str(raw_path), bgr)
        proc = subprocess.run(
            [sys.executable, '-c', _DETECT_SCRIPT, str(raw_path), str(out_path)],
            capture_output=True, text=True, timeout=30,
        )
        print(proc.stdout.strip())
        if proc.stderr.strip():
            print(proc.stderr.strip(), file=sys.stderr)
        for line in proc.stdout.splitlines():
            if line.startswith('DETECTED_IDS='):
                body = line.split('=', 1)[1].strip()
                if body in ('[]', 'none', ''):
                    return []
                # e.g. [0] or [0, 1]
                body = body.strip('[]')
                if not body:
                    return []
                return [int(x.strip()) for x in body.split(',') if x.strip()]
        return []
    finally:
        raw_path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=None)
    parser.add_argument('--target-yaw', type=float, default=math.pi / 2)
    parser.add_argument('--image-timeout', type=float, default=90.0)
    parser.add_argument('--attempts', type=int, default=10)
    args, _unknown = parser.parse_known_args(argv)

    out = args.output or (_repo_root() / 'docs' / 'images' / 'phase1_aruco_camera.png')
    out.parent.mkdir(parents=True, exist_ok=True)

    # Close to door 0, facing +Y. Prefer gz set_pose so we do not fight
    # odom (set_pose does not reset the bridged odom frame).
    posed = try_set_pose_gz(-3.5, 1.20, args.target_yaw)
    time.sleep(0.8)

    rclpy.init()
    node = ArucoVerifier()
    try:
        print('Waiting for /camera/image_raw ...')
        node.wait_for_image(args.image_timeout)
        print('Camera OK')
        if not posed:
            print(f'Facing yaw={args.target_yaw:.3f} via TwistStamped /cmd_vel')
            node.face_yaw(args.target_yaw)
            time.sleep(0.5)
        else:
            print('Using gz set_pose orientation (skip odom face_yaw)')

        detected: list[int] = []
        for attempt in range(1, args.attempts + 1):
            # Re-assert pose each attempt: cmd_vel nudges desync odom/map
            if posed:
                try_set_pose_gz(-3.5, 1.20 + 0.05 * (attempt - 1), args.target_yaw)
                time.sleep(0.4)
            frame = node.wait_for_image(10.0)
            detected = detect_in_subprocess(frame, out)
            print(f'Attempt {attempt}: detected IDs = {detected}')
            if detected:
                break
            if not posed:
                for _ in range(6):
                    node.publish_cmd(linear_x=0.08)
                    rclpy.spin_once(node, timeout_sec=0.0)
                    time.sleep(0.05)
                node.publish_cmd()
                time.sleep(0.3)
                node.face_yaw(args.target_yaw)

        print(f'Saved {out}')
        print(f'DETECTED_IDS={detected}')
        return 0 if detected else 2
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    raise SystemExit(main())
