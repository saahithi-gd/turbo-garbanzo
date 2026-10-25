#!/usr/bin/env bash
# Wait for Nav2, then send 5 school_floor goals via nav2_simple_commander.
#
# Usage:
#   ./scripts/run_nav.sh &            # terminal 1
#   ./scripts/run_nav_goals.sh        # terminal 2 (after Nav2 is up)
#
# Or one-shot (starts Nav2 headless in background if /navigate_to_pose missing):
#   ./scripts/run_nav_goals.sh --with-nav
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"

ROOT="${ASTROPATH_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
LOG="${ROOT}/docs/nav_goals_log.txt"
WITH_NAV=false
NAV_PID=""

for arg in "$@"; do
  case "${arg}" in
    --with-nav) WITH_NAV=true ;;
    --help|-h)
      echo "Usage: $0 [--with-nav]"
      exit 0
      ;;
  esac
done

cleanup() {
  if [[ -n "${NAV_PID}" ]] && kill -0 "${NAV_PID}" 2>/dev/null; then
    echo "[run_nav_goals] Stopping background Nav2 (pid ${NAV_PID})"
    kill "${NAV_PID}" 2>/dev/null || true
    wait "${NAV_PID}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

has_nav() {
  ros2 action list 2>/dev/null | grep -q '/navigate_to_pose'
}

if ! has_nav; then
  if [[ "${WITH_NAV}" != true ]]; then
    echo "[run_nav_goals] Nav2 not detected. Start ./scripts/run_nav.sh or pass --with-nav" >&2
    exit 1
  fi
  echo "[run_nav_goals] Starting ./scripts/run_nav.sh (headless) in background…"
  "${SCRIPT_DIR}/run_nav.sh" --headless >/tmp/astropath_run_nav.log 2>&1 &
  NAV_PID=$!
fi

echo "[run_nav_goals] Waiting for /navigate_to_pose…"
READY=0
for _ in $(seq 1 180); do
  if has_nav; then
    READY=1
    break
  fi
  sleep 1
done
if [[ "${READY}" -ne 1 ]]; then
  echo "[run_nav_goals] ERROR: Nav2 did not come up (see /tmp/astropath_run_nav.log)" >&2
  exit 1
fi

# Extra settle for AMCL + costmaps after action server appears
sleep 8

echo "[run_nav_goals] Running nav_goals → ${LOG}"
export NAV_GOALS_LOG="${LOG}"
set +e
ros2 run astropath_config nav_goals --ros-args -p use_sim_time:=true
RC=$?
set -e

echo "[run_nav_goals] exit=${RC}"
if [[ -f "${LOG}" ]]; then
  echo "----- ${LOG} -----"
  cat "${LOG}"
fi
exit "${RC}"
