#!/usr/bin/env bash
# Launch school_floor + slam_toolbox online async for mapping.
#
# Usage:
#   ./scripts/run_slam.sh                 # headless sim + SLAM (default)
#   ./scripts/run_slam.sh --gui           # with Gazebo client (PRIME)
#   ./scripts/run_slam.sh --explore       # also auto-run school_explorer
#   ./scripts/run_slam.sh --no-sim        # SLAM only (sim already running)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"

GUI=false
START_SIM=true
START_EXPLORER=false
for arg in "$@"; do
  case "${arg}" in
    --gui) GUI=true ;;
    --headless) GUI=false ;;
    --explore) START_EXPLORER=true ;;
    --no-sim) START_SIM=false ;;
    --help|-h)
      echo "Usage: $0 [--gui|--headless] [--explore] [--no-sim]"
      exit 0
      ;;
  esac
done

export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-waffle}"
echo "[run_slam] gui=${GUI} start_sim=${START_SIM} explore=${START_EXPLORER}"
echo "[run_slam] use_sim_time:=true  TURTLEBOT3_MODEL=${TURTLEBOT3_MODEL}"

exec ros2 launch astropath_config slam_school.launch.py \
  use_sim_time:=true \
  gui:="${GUI}" \
  start_sim:="${START_SIM}" \
  start_explorer:="${START_EXPLORER}"
