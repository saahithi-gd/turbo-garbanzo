#!/usr/bin/env bash
# Run the simple island-wall hallway waypoint loop (Nav2 FollowWaypoints).
#
# Prereq: Nav2 already up via ./scripts/run_nav.sh [--gui]
#
# Usage:
#   ./scripts/run_simple_route.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"

echo "[simple_route] ensuring Nav2 navigation lifecycle is active…"
"${SCRIPT_DIR}/fix_nav_lifecycle.sh" || true

echo "[simple_route] island-wall loop via FollowWaypoints (use_sim_time)"
echo "[simple_route] In RViz: Fixed Frame=map; you should see a green path, then motion"
exec ros2 run astropath_config simple_route --ros-args -p use_sim_time:=true