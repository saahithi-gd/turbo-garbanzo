#!/usr/bin/env bash
# Activate Nav2 navigation nodes if lifecycle manager left them inactive.
# Skips docking_server (not used by Astropath).
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"

echo "[nav_lifecycle] trying lifecycle RESUME…"
ros2 service call /lifecycle_manager_navigation/manage_nodes \
  nav2_msgs/srv/ManageLifecycleNodes "{command: 2}" || true
sleep 1

activate() {
  local n=$1
  ros2 service call "/${n}/change_state" lifecycle_msgs/srv/ChangeState \
    "{transition: {id: 3, label: 'activate'}}" >/dev/null 2>&1 || true
}

for n in controller_server smoother_server planner_server route_server \
         behavior_server velocity_smoother collision_monitor \
         bt_navigator waypoint_follower; do
  activate "${n}"
done
sleep 1

echo "[nav_lifecycle] node states:"
for n in amcl planner_server bt_navigator waypoint_follower controller_server; do
  st=$(ros2 service call "/${n}/get_state" lifecycle_msgs/srv/GetState {} 2>/dev/null \
    | grep -o "label='[^']*'" | head -1 || echo "label='?'")
  echo "  ${n}: ${st}"
done
