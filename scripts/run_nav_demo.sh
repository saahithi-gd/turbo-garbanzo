#!/usr/bin/env bash
# One-shot demo: school_floor + Nav2 + RViz, then the simple wall route.
#
# Usage:
#   ./scripts/run_nav_demo.sh           # Gazebo GUI + RViz + auto route
#   ./scripts/run_nav_demo.sh --no-rviz # skip RViz
#   ./scripts/run_nav_demo.sh --no-route  # just bringup (you send goals later)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"

START_RVIZ=true
START_ROUTE=true
for arg in "$@"; do
  case "${arg}" in
    --no-rviz) START_RVIZ=false ;;
    --no-route) START_ROUTE=false ;;
    --help|-h)
      echo "Usage: $0 [--no-rviz] [--no-route]"
      exit 0
      ;;
  esac
done

# Clean stale sims so AMCL/clock are not confused
pkill -f 'gz sim.*school_floor' 2>/dev/null || true
pkill -f 'nav2_|bt_navigator|amcl|map_server' 2>/dev/null || true
sleep 1

RVIZ_CFG="/opt/ros/jazzy/share/nav2_bringup/rviz/nav2_default_view.rviz"
TB3_RVIZ="${ASTROPATH_ROOT}/ros2_ws/src/turtlebot3/turtlebot3_navigation2/rviz/tb3_navigation2.rviz"
if [[ -f "${TB3_RVIZ}" ]]; then
  RVIZ_CFG="${TB3_RVIZ}"
fi

echo "[nav_demo] launching school_floor + Nav2 (GUI=true)"
ros2 launch astropath_config nav_school.launch.py \
  use_sim_time:=true \
  gui:=true \
  start_sim:=true \
  autostart:=true &
NAV_PID=$!

cleanup() {
  kill "${NAV_PID}" 2>/dev/null || true
  pkill -f 'gz sim.*school_floor' 2>/dev/null || true
}
trap cleanup EXIT

echo "[nav_demo] waiting 20s for Gazebo + Nav2 lifecycle…"
sleep 20

if [[ "${START_RVIZ}" == true ]]; then
  echo "[nav_demo] RViz: ${RVIZ_CFG}"
  echo "[nav_demo] In RViz: Fixed Frame = map; you should see map, robot, costmaps, plan"
  rviz2 -d "${RVIZ_CFG}" &
  RVIZ_PID=$!
  trap 'kill "${RVIZ_PID}" 2>/dev/null || true; cleanup' EXIT
  sleep 3
fi

if [[ "${START_ROUTE}" == true ]]; then
  echo "[nav_demo] starting simple island-wall waypoint route…"
  ros2 run astropath_config simple_route --ros-args -p use_sim_time:=true
  echo "[nav_demo] route finished (exit=$?). Leave windows open; Ctrl+C to stop."
  # Keep demo up for viewing
  wait "${NAV_PID}"
else
  echo "[nav_demo] bringup only. Send route with: ./scripts/run_simple_route.sh"
  wait "${NAV_PID}"
fi
