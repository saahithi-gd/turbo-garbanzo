# Learning Log

Interview-friendly notes for each phase. Fill in **In my own words** after
completing the hands-on work — that section is what you actually say out loud.

---

## Phase 0 — Bootstrap: ROS 2 Jazzy + Gazebo Harmonic + TurtleBot3

### What we set up

- Native Ubuntu 24.04 with ROS 2 Jazzy desktop and Gazebo Harmonic already on the machine.
- Confirmed the official pairing: **Jazzy ↔ Harmonic** via `ros_gz` (no Ignition/Gazebo Classic conflict).
- Pulled ROBOTIS TurtleBot3 packages on the **jazzy** branch (pinned SHAs in `astropath.repos`), including DynamixelSDK as required by the e-Manual build.
- Hybrid laptop GPU (AMD iGPU + NVIDIA RTX 4070): Gazebo/OpenGL uses **PRIME render offload** so the discrete GPU drives the sim without switching the whole session.
- Avoided conda’s Python 3.13 on `PATH` for ROS work — ROS Jazzy expects system Python 3.12 (`/usr/bin/python3`).
- Smoke-tested `turtlebot3_world`, verified bridged sensor topics, and confirmed `cmd_vel` moves the robot.

### Why it matters (interview angle)

Phase 0 is the “reproducible robotics workstation” story: pin dependencies, document
platform decisions (distro pairing, GPU offload, Python), and prove the sim stack
runs before writing any custom world or Nav2 config. Interviewers care that you can
bring up a known-good baseline and debug topic bridges (`ros_gz_bridge`) rather than
jumping straight into navigation parameters.

### Key concepts touched

- `vcs` / `.repos` pinning for multi-repo workspaces
- `colcon build --symlink-install`
- Gazebo Harmonic + `ros_gz_sim` (server/client split)
- PRIME offload (`__NV_PRIME_RENDER_OFFLOAD`, `__GLX_VENDOR_LIBRARY_NAME`)
- `use_sim_time` and `TURTLEBOT3_MODEL`

### In my own words

<!-- Fill after running install + smoke test yourself -->

### Phase 0 gotchas worth memorizing

- Jazzy TB3 `/cmd_vel` is **`TwistStamped`**, not `Twist`.
- Fuel CDN can 502 — Astropath `install.sh` patches worlds to inline Ground Plane/Sun.
- Never let conda Python 3.13 drive `colcon` / ament on this machine.

---

## Phase 1 — Custom school_floor world + ArUco door markers

### What we built

- New ROS 2 package `astropath_sim` with a Gazebo Harmonic world `school_floor`: hallway loop, four rooms (one **narrow ~0.7 m** door), a dead-end spur, and simple box/locker clutter.
- ArUco door markers **IDs 0–3** (`DICT_4X4_50`), generated with system OpenCV and textured onto OBJ planes (box primitives did not get usable UVs).
- Launch file mirrors TB3 jazzy: `ros_gz_sim` server/client, `spawn_turtlebot3.launch.py`, `robot_state_publisher`, `GZ_SIM_RESOURCE_PATH` for TB3 + astropath models, `use_sim_time:=true`.
- Runner `./scripts/run_school.sh` and regenerator `./scripts/generate_aruco_markers.py`.
- Acceptance: waffle faces door 0, `/camera/image_raw` captures marker, OpenCV detects **ID 0** → `docs/images/phase1_aruco_camera.png`.

### Why it matters (interview angle)

Phase 1 is the “custom environment for perception” story: you design a world that stresses navigation later (narrow door, dead end, loop) and prove a camera pipeline can read semantic landmarks (ArUco). Interviewers like hearing that you matched upstream launch conventions instead of inventing a one-off spawn stack, and that you debugged sim rendering (FOV, materials, texture UVs) until detection worked—not just that you dropped PNGs into a folder.

### Key concepts touched

- ament_python package with `data_files` for worlds/models/launch
- Gazebo Harmonic SDF worlds with local sun/ground (no Fuel)
- `model://` resources + `GZ_SIM_RESOURCE_PATH`
- ArUco `DICT_4X4_50` generation and detection
- TurtleBot3 waffle camera height / vertical FOV vs marker size and stand-off

### In my own words

<!-- Fill after running school_floor + ArUco verify yourself -->

### Phase 1 gotchas worth memorizing

- Waffle camera sits ~0.1 m high with a narrow vertical FOV — markers must be **low and small enough** to fit fully in frame.
- PBR `emissive` on marker materials washes blacks to gray and kills detection; keep emissive off.
- Prefer textured **meshes with UVs** over bare boxes for ArUco albedo maps.
- Stock spawn has no yaw arg — face a door with `gz` set_pose and/or **`TwistStamped`** on `/cmd_vel`.

---

## Phase 2 — Mapping school_floor (clean map for Nav2)

### What we built

- New package `astropath_config` with slam_toolbox online-async params, `slam_school.launch.py`, and a gentle `school_explorer` (TwistStamped, ~0.12 m/s).
- Runners `./scripts/run_slam.sh` and `./scripts/save_map.sh` for a live SLAM → map_saver path.
- **Committed map is geometry-derived** from SDF wall boxes (`scripts/generate_school_map.py`) because a first SLAM pass ghosted; preview at `docs/images/school_floor_map.png`.

### Why it matters (interview angle)

Phase 2 is the “map quality gates navigation” story: SLAM is the real-robot path, but for sim demos a smeared map silently breaks AMCL. Choosing a ground-truth occupancy grid from known geometry is an honest engineering tradeoff—document it, keep the SLAM pipeline, and move on to Nav2 with a map you trust.

### Key concepts touched

- slam_toolbox online async + pose-graph loop closure
- Occupancy grid PGM/YAML (`map_server` / `map_saver_cli`)
- `use_sim_time` during mapping
- TwistStamped teleop/explorer vs stock Twist teleop

### In my own words

<!-- Fill after running SLAM explorer and/or regenerating the geometry map -->

### Phase 2 gotchas worth memorizing

- Ghosted walls = loop-close / scan-match drift; slow down and prefer one clean loop.
- For AMCL, a wrong map is worse than no map — validate the PNG before Nav2.
- Geometry map and SLAM map share the same path; regenerating overwrites.