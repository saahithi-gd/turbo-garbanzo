#!/usr/bin/env bash
# Idempotent Phase 0 installer for Astropath (ROS 2 Jazzy + Gazebo Harmonic + TB3).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
WS="${ROOT}/ros2_ws"
REPOS_FILE="${ROOT}/astropath.repos"
SRC="${WS}/src"

log()  { printf '\n==> %s\n' "$*"; }
warn() { printf 'WARNING: %s\n' "$*" >&2; }
die()  { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

# Elevate: prefer passwordless sudo, then pkexec (GUI polkit), then interactive sudo.
run_root() {
  if sudo -n true 2>/dev/null; then
    sudo "$@"
  elif command -v pkexec >/dev/null 2>&1; then
    pkexec "$@"
  else
    sudo "$@"
  fi
}

# ---------------------------------------------------------------------------
# 0. Keep conda / wrong Python out of ROS builds
# ---------------------------------------------------------------------------
if [[ -n "${CONDA_DEFAULT_ENV:-}" ]] && command -v conda >/dev/null 2>&1; then
  conda deactivate 2>/dev/null || true
fi
# Strip conda from PATH and clear hints that leak into CMake FindPython.
PATH="$(echo "${PATH:-/usr/bin:/bin}" | tr ':' '\n' | grep -v -E '/yes/(bin|condabin)|/miniconda|/anaconda' | paste -sd: -)"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:${PATH}"
unset CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_PYTHON_EXE CONDA_SHLVL CONDA_PROMPT_MODIFIER || true
unset PYTHONHOME PYTHONPATH || true
export Python3_ROOT_DIR=/usr
export Python3_EXECUTABLE=/usr/bin/python3
export PYTHON_EXECUTABLE=/usr/bin/python3

PY="$(command -v python3)"
PY_VER="$("${PY}" -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
log "Using python3=${PY} (${PY_VER})"
[[ "${PY}" == "/usr/bin/python3" ]] || warn "python3 is not /usr/bin/python3 — ROS builds may fail"
[[ "${PY_VER}" == "3.12" ]] || warn "Expected system Python 3.12 for Jazzy; got ${PY_VER}"

# ---------------------------------------------------------------------------
# 1. OS check
# ---------------------------------------------------------------------------
log "Detecting OS"
[[ -f /etc/os-release ]] || die "/etc/os-release missing"
# shellcheck disable=SC1091
source /etc/os-release
echo "  PRETTY_NAME=${PRETTY_NAME:-unknown}"
echo "  ID=${ID:-?} VERSION_ID=${VERSION_ID:-?}"
if [[ "${ID}" != "ubuntu" ]] || [[ "${VERSION_ID}" != "24.04" ]]; then
  warn "This project targets Ubuntu 24.04 + ROS Jazzy; continuing anyway."
fi

# ---------------------------------------------------------------------------
# 2. GPU PRIME offload exports (for any GL checks during install)
# ---------------------------------------------------------------------------
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __VK_LAYER_NV_optimus=NVIDIA_only

# ---------------------------------------------------------------------------
# 3. apt dependencies (idempotent)
# ---------------------------------------------------------------------------
log "Installing apt dependencies (sudo)"
APT_PKGS=(
  curl
  wget
  git
  mesa-utils
  python3-pip
  python3-colcon-common-extensions
  python3-rosdep
  python3-vcstool
  python3-opencv
  python3-numpy
  python3-pandas
  python3-matplotlib
  python3-yaml
  ros-jazzy-ros-gz
  ros-jazzy-ros-gz-sim
  ros-jazzy-ros-gz-bridge
  ros-jazzy-ros-gz-image
  ros-jazzy-navigation2
  ros-jazzy-nav2-bringup
  ros-jazzy-slam-toolbox
  ros-jazzy-teleop-twist-keyboard
  ros-jazzy-xacro
  ros-jazzy-robot-state-publisher
  ros-jazzy-joint-state-publisher
  ros-jazzy-tf-transformations
  ros-jazzy-topic-tools
  ros-jazzy-hls-lfcd-lds-driver
  ros-jazzy-cartographer-ros
  python3-catkin-pkg
)

# Single elevated session so polkit/pkexec only prompts once.
APT_PKGS_STR="${APT_PKGS[*]}"
run_root bash -c "
  set -euo pipefail
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y --no-install-recommends ${APT_PKGS_STR}
  if [[ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]]; then
    rosdep init || true
  fi
"

rosdep update || warn "rosdep update failed (network?); continuing"

# ---------------------------------------------------------------------------
# 4. Keep duplicate repos file in sync
# ---------------------------------------------------------------------------
mkdir -p "${SRC}"
cp -f "${REPOS_FILE}" "${WS}/astropath.repos"

# ---------------------------------------------------------------------------
# 5. vcs import pinned ROBOTIS repos
# ---------------------------------------------------------------------------
log "Importing repositories from ${REPOS_FILE}"
[[ -f "${REPOS_FILE}" ]] || die "Missing ${REPOS_FILE}"
# --skip-existing keeps re-runs idempotent; pinned SHAs enforced via version field on first clone.
# For already-cloned repos, checkout the pinned SHA explicitly.
vcs import --input "${REPOS_FILE}" --skip-existing "${SRC}"

# Ensure each repo is exactly at the pinned SHA (handles re-runs after drift).
python3 - "${REPOS_FILE}" "${SRC}" <<'PY'
import sys, yaml, subprocess, os
repos_file, src = sys.argv[1], sys.argv[2]
with open(repos_file) as f:
    data = yaml.safe_load(f)
for name, meta in data.get("repositories", {}).items():
    path = os.path.join(src, name)
    sha = meta["version"]
    if not os.path.isdir(os.path.join(path, ".git")):
        print(f"  missing clone: {path}", file=sys.stderr)
        sys.exit(1)
    subprocess.check_call(["git", "-C", path, "fetch", "--quiet", "origin"], stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "-C", path, "checkout", "--quiet", "--detach", sha])
    head = subprocess.check_output(["git", "-C", path, "rev-parse", "HEAD"], text=True).strip()
    print(f"  {name}: {head}")
    if head != sha:
        print(f"  SHA mismatch for {name}: got {head} want {sha}", file=sys.stderr)
        sys.exit(1)
PY

# ---------------------------------------------------------------------------
# 5b. Patch TB3 worlds: Fuel Ground Plane/Sun → inline SDF (offline-safe)
# ---------------------------------------------------------------------------
log "Patching TB3 worlds for Fuel CDN independence"
WORLDS_DIR="${SRC}/turtlebot3_simulations/turtlebot3_gazebo/worlds"
python3 "${SCRIPT_DIR}/patch_tb3_fuel_models.py" "${WORLDS_DIR}"

# ---------------------------------------------------------------------------
# 6. rosdep install for workspace (idempotent)
# ---------------------------------------------------------------------------
log "rosdep install for workspace"
# ROS setup scripts reference optional vars; tolerate unbound under set -u.
set +u
# shellcheck disable=SC1091
source /opt/ros/jazzy/setup.bash
set -u
# rosdep shells out to `sudo -H apt-get`; shim sudo → run_root when needed.
sudo() {
  if [[ "${1:-}" == "-H" ]]; then
    shift
  fi
  run_root "$@"
}
export -f sudo run_root
rosdep install --from-paths "${SRC}" --ignore-src -r -y \
  --rosdistro jazzy || warn "rosdep install reported issues; continuing to build"
unset -f sudo

# ---------------------------------------------------------------------------
# 7. colcon build
# ---------------------------------------------------------------------------
log "colcon build --symlink-install"
cd "${WS}"
# DynamixelSDK ships nested ROS packages under ros/; TB3 expects them discoverable.
# COLCON builds all packages under src/ recursively by default.
set +u
# Wipe stale CMake caches that may have captured conda python from a prior run.
if [[ -d "${WS}/build" ]]; then
  find "${WS}/build" -name CMakeCache.txt -delete 2>/dev/null || true
fi
colcon build --symlink-install --cmake-args \
  -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE=/usr/bin/python3 \
  -DPYTHON_EXECUTABLE=/usr/bin/python3
set -u

# ---------------------------------------------------------------------------
# 8. Done
# ---------------------------------------------------------------------------
log "Install complete"
echo
echo "  Source the environment in every new shell:"
echo "    source ${ROOT}/scripts/env.sh"
echo
echo "  Smoke-test TurtleBot3 world:"
echo "    ${ROOT}/scripts/run_tb3_world.sh"
echo
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "  GPU:"
  nvidia-smi --query-gpu=name,driver_version --format=csv,noheader || true
fi
if command -v glxinfo >/dev/null 2>&1; then
  echo "  OpenGL (PRIME offload):"
  __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia \
    glxinfo -B 2>/dev/null | grep -E 'OpenGL (vendor|renderer|version)' || true
fi
