# ROS 2 Jazzy & Gazebo Turtlebot Nav2 Navigation

Astropath is a ROS 2 Jazzy robotics project where a TurtleBot3 Waffle navigates a custom school-style world in Gazebo Harmonic. It covers mapping, AMCL localization, and Nav2 path planning for autonomous hallway routes. The sim includes dense rooms, narrow doors, and ArUco markers on doorways for room-level goals. The goal is a clear, end-to-end Nav2 portfolio demo of perception-linked mobile navigation.

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

# Mapping
./scripts/run_slam.sh --explore      # headless school + slam_toolbox + explorer
./scripts/save_map.sh                # save live /map (if remapping via SLAM)
/usr/bin/python3 ./scripts/generate_school_map.py   # regenerate geometry map

# Nav2 hallway route
./scripts/run_nav.sh --gui                                    # Terminal A
rviz2 -d /opt/ros/jazzy/share/nav2_bringup/rviz/nav2_default_view.rviz \
  --ros-args -p use_sim_time:=true                            # Terminal B

./scripts/run_simple_route.sh                                 # Terminal C (~20s after A)

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
