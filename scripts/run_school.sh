#!/usr/bin/env bash
# Launch Astropath school_floor world (Gazebo Harmonic + TurtleBot3 Waffle).
#
# Usage:
#   ./scripts/run_school.sh              # gz server + GUI client (PRIME offload)
#   ./scripts/run_school.sh --headless   # gz server only (no GUI client)
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

GUI_ARG=true
if [[ "${HEADLESS}" -eq 1 ]]; then
  GUI_ARG=false
  echo "[run_school] headless: server + spawn + robot_state_publisher (no gz client)"
else
  echo "[run_school] GUI with PRIME offload (__NV_PRIME_RENDER_OFFLOAD=${__NV_PRIME_RENDER_OFFLOAD:-})"
fi

echo "[run_school] TURTLEBOT3_MODEL=${TURTLEBOT3_MODEL}"
echo "[run_school] launching astropath_sim school_floor.launch.py gui:=${GUI_ARG}"
exec ros2 launch astropath_sim school_floor.launch.py \
  use_sim_time:=true \
  gui:="${GUI_ARG}"
