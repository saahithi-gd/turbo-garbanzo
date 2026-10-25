#!/usr/bin/env bash
# Smoke-test launcher: stock TurtleBot3 world (Gazebo Harmonic via ros_gz).
#
# Usage:
#   ./scripts/run_tb3_world.sh              # gz server + GUI client (PRIME offload)
#   ./scripts/run_tb3_world.sh --headless   # gz server only (no GUI client)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"

HEADLESS=0
for arg in "$@"; do
  case "${arg}" in
    --headless) HEADLESS=1 ;;
    --help|-h)
      echo "Usage: $0 [--headless]"
      exit 0
      ;;
  esac
done

command -v ros2 >/dev/null 2>&1 || { echo "ros2 not on PATH — source env.sh first" >&2; exit 1; }

export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-waffle}"

# Stock turtlebot3_world.launch.py always starts both gz server (-s) and client (-g).
# For headless, launch the same pieces without the GUI client include.
if [[ "${HEADLESS}" -eq 1 ]]; then
  echo "[run_tb3_world] headless: server + spawn + robot_state_publisher (no gz client)"
  WORLD="$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/worlds/turtlebot3_world.world"
  MODELS="$(ros2 pkg prefix turtlebot3_gazebo)/share/turtlebot3_gazebo/models"
  export GZ_SIM_RESOURCE_PATH="${MODELS}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
  exec ros2 launch "${SCRIPT_DIR}/tb3_world_headless.launch.py" \
    world:="${WORLD}" \
    use_sim_time:=true \
    x_pose:=-2.0 \
    y_pose:=-0.5
fi

echo "[run_tb3_world] GUI with PRIME offload (__NV_PRIME_RENDER_OFFLOAD=${__NV_PRIME_RENDER_OFFLOAD:-})"
echo "[run_tb3_world] TURTLEBOT3_MODEL=${TURTLEBOT3_MODEL}"
echo "[run_tb3_world] launching turtlebot3_gazebo turtlebot3_world.launch.py"
exec ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py
