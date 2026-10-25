#!/usr/bin/env bash
# Launch school_floor + Nav2 (map_server, AMCL, navigation) for Phase 3.
#
# Usage:
#   ./scripts/run_nav.sh              # headless sim + Nav2 (default)
#   ./scripts/run_nav.sh --gui        # with Gazebo client (PRIME)
#   ./scripts/run_nav.sh --no-sim     # Nav2 only (sim already running)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"

GUI=false
START_SIM=true
for arg in "$@"; do
  case "${arg}" in
    --gui) GUI=true ;;
    --headless) GUI=false ;;
    --no-sim) START_SIM=false ;;
    --help|-h)
      echo "Usage: $0 [--gui|--headless] [--no-sim]"
      exit 0
      ;;
  esac
done

export TURTLEBOT3_MODEL="${TURTLEBOT3_MODEL:-waffle}"
echo "[run_nav] gui=${GUI} start_sim=${START_SIM}"
echo "[run_nav] use_sim_time:=true  TURTLEBOT3_MODEL=${TURTLEBOT3_MODEL}"
echo "[run_nav] TwistStamped: nav2_params enable_stamped_cmd_vel:=true (TB3 waffle)"
echo "[run_nav] TIP: if robot won't move, run: ./scripts/fix_nav_lifecycle.sh"
echo "[run_nav] RViz with sim time:"
echo "         rviz2 -d /opt/ros/jazzy/share/nav2_bringup/rviz/nav2_default_view.rviz --ros-args -p use_sim_time:=true"

exec ros2 launch astropath_config nav_school.launch.py \
  use_sim_time:=true \
  gui:="${GUI}" \
  start_sim:="${START_SIM}" \
  autostart:=true