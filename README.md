# ROS 2 Jazzy + Gazebo Turtlebot Nav2 Navigation

TurtleBot3 Waffle in a custom school-style Gazebo world: SLAM/mapping, Nav2 hallway navigation, and ArUco door markers for room goals.

## Quick start

```bash
# One-time (or re-run anytime — idempotent)
./scripts/install.sh

# Every new shell
source ./scripts/env.sh

# Stock TB3 smoke world
./scripts/run_tb3_world.sh

# Astropath school_floor (Waffle + ArUco doors)
./scripts/run_school.sh              # GUI + PRIME offload
./scripts/run_school.sh --headless   # server only

# Regenerate ArUco PNGs (DICT_4X4_50 IDs 0–3)
/usr/bin/python3 ./scripts/generate_aruco_markers.py

# After school_floor is up: detect door marker 0 from the camera
ros2 run astropath_sim verify_aruco_camera

# Mapping
./scripts/run_slam.sh --explore      # headless school + slam_toolbox + explorer
./scripts/save_map.sh                # save live /map (if remapping via SLAM)
/usr/bin/python3 ./scripts/generate_school_map.py   # regenerate geometry map

# Nav2 hallway route
./scripts/run_nav.sh --gui                                    # Terminal A
rviz2 -d /opt/ros/jazzy/share/nav2_bringup/rviz/nav2_default_view.rviz \
  --ros-args -p use_sim_time:=true                            # Terminal B
./scripts/fix_nav_lifecycle.sh                              # if Nav2 looks stuck
./scripts/run_simple_route.sh                                 # Terminal C (~20s after A)
# Or one-shot: ./scripts/run_nav_demo.sh
```

## Stack

| Piece           | Choice                                      |
|-----------------|---------------------------------------------|
| OS              | Ubuntu 24.04 LTS (native)                   |
| ROS             | ROS 2 Jazzy                                 |
| Simulator       | Gazebo Harmonic (`ros_gz`)                  |
| Robot           | TurtleBot3 Waffle (jazzy branch)            |
| Navigation      | Nav2 (`navigation2`, `nav2_bringup`)        |
| Localization    | AMCL + map_server                           |
| Mapping         | slam_toolbox (online async)                 |
| Commander API   | nav2_simple_commander                       |
| Perception      | OpenCV ArUco (`DICT_4X4_50`)                |
| Helpers         | pandas, matplotlib, numpy, PyYAML           |

See [docs/DECISIONS.md](docs/DECISIONS.md) and [LEARNING.md](LEARNING.md).
