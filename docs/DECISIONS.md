# Decisions Log

Running record of platform and stack choices for Astropath.

---

## Phase 0 — Environment & baseline stack

### Host OS

- **Choice:** Ubuntu 24.04.3 LTS **native** (not WSL).
- **Why:** Gazebo Harmonic + NVIDIA PRIME offload are simplest on bare metal; WSL adds GPU/GUI friction for sim.

### ROS / Gazebo pairing

- **Choice:** ROS 2 **Jazzy** + Gazebo **Harmonic** (`gz-harmonic`), bridged with `ros_gz`.
- **Why:** Official recommended pairing for Jazzy. Confirmed no conflict with Classic/Ignition — Harmonic is the supported sim for this distro.
- **Packages:** `ros-jazzy-desktop` and `gz-harmonic` already installed on host; Phase 0 install adds `ros-jazzy-ros-gz`, Nav2, slam_toolbox, teleop, etc.

### TurtleBot3 branch

- **Choice:** ROBOTIS **jazzy** branches for `turtlebot3`, `turtlebot3_msgs`, `turtlebot3_simulations`, and `DynamixelSDK`.
- **Why:** e-Manual documents Jazzy + Ubuntu 24.04 + `gz-harmonic`; jazzy branches use `ros_gz` (Harmonic), not Classic.
- **Pins** (verified `git ls-remote` 2026-03-22 against `refs/heads/jazzy`):

  | Repo                     | SHA                                        |
  |--------------------------|--------------------------------------------|
  | turtlebot3_simulations   | `45633014a14e8f438495b532a723e4ad45cbbd31` |
  | turtlebot3               | `0c0be84e3f5c3194fb2adea8426a58a96060eab5` |
  | turtlebot3_msgs          | `9209e01b4708cf3ca5610b01dfc9586d3c7889d8` |
  | DynamixelSDK             | `516ae8632c593d7c84afd2bdee2a2fac965305cc` |

- DynamixelSDK is included even for sim-only Phase 0 because the e-Manual and TB3 package build expect it in the workspace.

### GPU (hybrid AMD + NVIDIA)

- **Hardware:** AMD iGPU (`amdgpu`) + NVIDIA RTX 4070 Laptop GPU, driver **580.173.02**.
- **Choice:** PRIME render offload for Gazebo / GLX:

  ```bash
  export __NV_PRIME_RENDER_OFFLOAD=1
  export __GLX_VENDOR_LIBRARY_NAME=nvidia
  ```

- **Why:** Session stays on the iGPU for desktop; heavy OpenGL (gz client) offloads to the RTX. Documented in `scripts/env.sh` and `scripts/install.sh`.
- **Verification notes:** See “Smoke test results” below after Phase 0 run.

### Python / conda caveat

- Default interactive `PATH` puts conda first (`/home/sidg/yes/bin/python3` → **3.13**).
- System `/usr/bin/python3` is **3.12.3** — required for ROS Jazzy.
- **Rule:** For all ROS builds and launches, prefer `/usr/bin` ahead of conda (or leave conda inactive). `scripts/env.sh` and `scripts/install.sh` enforce this.

### Floorplan

- **No `floorplan.png` yet.** Phase 1+ will use a generic school-style layout; do not block Phase 0 on custom geometry.

### Workspace layout

- Canonical vcstool file: repo-root `astropath.repos`.
- Duplicate copy: `ros2_ws/astropath.repos` (same content) for layout consistency when working inside the workspace.
- Sources land in `ros2_ws/src/` via `vcs import`.

---

## Smoke test results (Phase 0)

Completed 2026-10-18 via `./scripts/install.sh` + `./scripts/run_tb3_world.sh` (GUI + PRIME offload).

### GPU

- `nvidia-smi`: **NVIDIA GeForce RTX 4070 Laptop GPU**, driver **580.173.02**
- `glxinfo` with PRIME offload:
  - OpenGL vendor: **NVIDIA Corporation**
  - OpenGL renderer: **NVIDIA GeForce RTX 4070 Laptop GPU/PCIe/SSE2**
  - OpenGL version: **4.6.0 NVIDIA 580.173.02**

### Topics observed (TurtleBot3 Waffle + ros_gz bridge)

Actual names match the waffle bridge YAML / image_bridge (leading `/`):

| Topic | Type | Notes |
|-------|------|-------|
| `/scan` | `sensor_msgs/msg/LaserScan` | ~10 Hz |
| `/odom` | `nav_msgs/msg/Odometry` | |
| `/tf` | `tf2_msgs/msg/TFMessage` | plus `/tf_static` |
| `/imu` | `sensor_msgs/msg/Imu` | ~200 Hz |
| `/camera/image_raw` | `sensor_msgs/msg/Image` | via `ros_gz_image` image_bridge (~24 Hz) |
| `/camera/camera_info` | `sensor_msgs/msg/CameraInfo` | |
| `/cmd_vel` | **`geometry_msgs/msg/TwistStamped`** | **not** plain `Twist` |
| `/clock` | `rosgraph_msgs/msg/Clock` | |
| `/joint_states` | `sensor_msgs/msg/JointState` | |

### Motion

- Published `geometry_msgs/msg/TwistStamped` on `/cmd_vel` (~4 s at 0.2 m/s + 0.3 rad/s).
- Odom XY displacement ≈ **1.04 m** → **MOTION_OK**.
- Note: stock `teleop_twist_keyboard` publishes `Twist`; Jazzy TB3 bridge expects **`TwistStamped`**. Use stamped pub or a twist→TwistStamped republisher for keyboard teleop.

### Issues / workarounds

1. **Fuel CDN 502:** Stock TB3 worlds include Ground Plane / Sun from `fuel.gazebosim.org`. During Phase 0 setup Fuel returned HTTP 502 and `gz sim` aborted before spawn. **Mitigation:** `scripts/patch_tb3_fuel_models.py` (run from `install.sh` after `vcs import`) replaces those includes with inline local SDF. Idempotent; re-applied on every install.
2. **sudo without TTY:** Non-interactive agent shells cannot prompt for `sudo` password. `install.sh` elevates via `sudo -n` if available, else **`pkexec`** (polkit GUI). Documented for future automation.
3. **conda Python 3.13 on PATH:** Broke first `colcon` attempt (`ament` invoked conda python missing `catkin_pkg`). `install.sh` / `env.sh` force `/usr/bin/python3` (3.12) and pass `-DPython3_EXECUTABLE=/usr/bin/python3`.
4. **`set -u` + ROS setup.bash:** Sourcing `/opt/ros/jazzy/setup.bash` under `nounset` fails on optional vars. `env.sh` temporarily disables `-u` while sourcing.

---

## Phase 1 — school_floor world & ArUco doors

### Layout

- **Choice:** Generic school-style layout (hallway loop, 4 rooms, dead end, clutter). **No `floorplan.png` yet** — geometry is placeholder until a real floorplan arrives.
- **Narrow door:** Room 3 south opening ≈ **0.7 m** (others ≈ 1.0 m) for later Nav2 choke-point demos.
- **Walls:** ~2.5 m tall box geometry; ground plane has ODE friction for future LiDAR mapping.

### ArUco

- **Dictionary:** OpenCV `DICT_4X4_50`, marker IDs **0, 1, 2, 3** on doors.
- **Generation:** `scripts/generate_aruco_markers.py` via `/usr/bin/python3` (not conda).
- **Models:** `aruco_marker_{id}` with OBJ + MTL + RGB PNG under `textures/` (TB3-house style paths). Box primitives alone did not receive reliable albedo UVs in Harmonic camera renders.

### Launch conventions

- Match TB3 jazzy: `ros_gz_sim` `gz_sim.launch.py` (`-r -s -v2` server, optional `-g` client), include `spawn_turtlebot3.launch.py` + `robot_state_publisher.launch.py`.
- Append `GZ_SIM_RESOURCE_PATH` for both `turtlebot3_gazebo/models` and `astropath_sim/models`.
- Default spawn: open hallway south of door 0 (`x=-3.5`, `y=1.2`), facing +X by default; verify script uses `gz` set_pose yaw=π/2 to face marker 0.
- GUI client uses `on_exit_shutdown:=false` so a gz-client segfault on this hybrid GPU host does not tear down the server.

### Fuel / CDN

- school_floor ships with **inline local sun + ground_plane** (same Phase 0 lesson — do not depend on Fuel).

### Issues / workarounds (Phase 1)

1. **Camera FOV vs marker height/size:** Markers at ~1.15 m were above waffle FOV; large 0.5–0.6 m markers overflowed the frame at hallway stand-off. Settled on ~0.30 m markers centered near z≈0.22 m, robot at y≈1.2 m.
2. **Texture washout:** High `emissive` on marker materials made “black” bits gray (~129–255) and broke ArUco decode. Emissive set to zero; sun diffuse reduced slightly.
3. **Box albedo UVs:** Thin box + PBR albedo showed a blank/washed plane; switched to UV’d OBJ planes.
4. **cv2.aruco + rclpy segfault:** In-process `detectMarkers` after `cv_bridge` segfaulted on this stack; verify runs detection in a **subprocess**.
5. **Multiple leftover `gz sim` processes:** Incomplete kills left parallel servers (namespaced `/clock`). Cleanup must kill both `gz` and `ruby /usr/bin/gz` wrappers before relaunch.
6. **`.gitignore`:** `ros2_ws/src/*` ignores vcs imports; whitelist `astropath_sim/` so the first-party package is committed.

---

## Phase 2 — Clean school_floor map (SLAM tooling + geometry map)

### Map source (Option B)

- **Choice:** **Geometry-derived** occupancy grid from `school_floor` SDF wall/clutter boxes (`scripts/generate_school_map.py`), not a live SLAM save.
- **Why:** An earlier slam_toolbox online-async pass produced a smeared/ghosted `school_floor.pgm` (loop-close drift on the hallway island). That map is unusable for AMCL. Rasterizing known box collisions yields a perfect sim map for Nav2 while keeping SLAM scripts for the portfolio story.
- **Artifacts:** `astropath_config/maps/school_floor.{pgm,yaml}` (0.05 m/cell, origin `[-8.0, -7.5, 0]`), preview `docs/images/school_floor_map.png`.

### SLAM tooling retained

- Package `astropath_config`: `slam_school.launch.py`, `mapper_params_online_async.yaml`, `school_explorer` (TwistStamped `/cmd_vel`, default **0.12 m/s**, turn-in-place).
- Runners: `./scripts/run_slam.sh` (`--explore` / `--gui` / `--no-sim`), `./scripts/save_map.sh` (`nav2_map_server map_saver_cli`).
- Explorer waypoints follow corridor-first room tour + island loop from model.sdf.

### Package layout

- `.gitignore` whitelists `astropath_config/` alongside `astropath_sim/`.
- Maps/params install via ament_python `data_files`.
