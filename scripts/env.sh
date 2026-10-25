#!/usr/bin/env bash
# Astropath ROS 2 environment — source from a login/interactive shell:
#   source /path/to/astropath/scripts/env.sh
#
# Safe to re-source. Does not activate conda (ROS Jazzy needs system Python 3.12).

# Resolve repo root even when sourced from elsewhere.
_ASTROPATH_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_ASTROPATH_ROOT="$(cd "${_ASTROPATH_ENV_DIR}/.." && pwd)"
unset _ASTROPATH_ENV_DIR

# Prefer system Python 3.12 over conda 3.13 for ROS tooling.
if [[ -n "${CONDA_DEFAULT_ENV:-}" ]] && command -v conda >/dev/null 2>&1; then
  # shellcheck disable=SC1091
  conda deactivate 2>/dev/null || true
fi
PATH="$(echo "${PATH:-/usr/bin:/bin}" | tr ':' '\n' | grep -v -E '/yes/(bin|condabin)|/miniconda|/anaconda' | paste -sd: -)"
export PATH="/usr/bin:/bin:/usr/sbin:/sbin:${PATH}"
unset CONDA_PREFIX CONDA_DEFAULT_ENV CONDA_PYTHON_EXE CONDA_SHLVL CONDA_PROMPT_MODIFIER 2>/dev/null || true
unset PYTHONHOME PYTHONPATH 2>/dev/null || true
export Python3_EXECUTABLE=/usr/bin/python3
export PYTHON_EXECUTABLE=/usr/bin/python3

# Hybrid GPU: offload OpenGL (Gazebo client) to NVIDIA via PRIME.
export __NV_PRIME_RENDER_OFFLOAD=1
export __GLX_VENDOR_LIBRARY_NAME=nvidia
export __VK_LAYER_NV_optimus=NVIDIA_only

# TurtleBot3 model used by TB3 launch files / URDF selectors.
export TURTLEBOT3_MODEL=waffle

# Simulation clocks — nodes that honor this will use /clock from Gazebo.
export ROS_USE_SIM_TIME=true

# Gazebo resource hints (Harmonic).
export GZ_SIM_RESOURCE_PATH="${GZ_SIM_RESOURCE_PATH:-}"
export GAZEBO_MODEL_PATH="${GAZEBO_MODEL_PATH:-}"

# Source ROS 2 Jazzy, then the overlay workspace if built.
# ROS setup scripts reference optional vars; tolerate unbound under set -u callers.
_astropath_had_u=0
case "$-" in *u*) _astropath_had_u=1; set +u ;; esac
if [[ -f /opt/ros/jazzy/setup.bash ]]; then
  # shellcheck disable=SC1091
  source /opt/ros/jazzy/setup.bash
else
  echo "[astropath env] WARNING: /opt/ros/jazzy/setup.bash not found" >&2
fi

_WS_SETUP="${_ASTROPATH_ROOT}/ros2_ws/install/setup.bash"
if [[ -f "${_WS_SETUP}" ]]; then
  # shellcheck disable=SC1091
  source "${_WS_SETUP}"
else
  echo "[astropath env] Workspace not built yet — run ./scripts/install.sh" >&2
fi
unset _WS_SETUP
[[ "${_astropath_had_u}" -eq 1 ]] && set -u
unset _astropath_had_u

# Append TB3 model paths after overlay so Gazebo finds ROBOTIS meshes/worlds.
if [[ -d "${_ASTROPATH_ROOT}/ros2_ws/src/turtlebot3_simulations/turtlebot3_gazebo/models" ]]; then
  _TB3_MODELS="${_ASTROPATH_ROOT}/ros2_ws/src/turtlebot3_simulations/turtlebot3_gazebo/models"
  _TB3_WORLDS="${_ASTROPATH_ROOT}/ros2_ws/src/turtlebot3_simulations/turtlebot3_gazebo/worlds"
  export GZ_SIM_RESOURCE_PATH="${_TB3_MODELS}:${_TB3_WORLDS}${GZ_SIM_RESOURCE_PATH:+:${GZ_SIM_RESOURCE_PATH}}"
  export GAZEBO_MODEL_PATH="${_TB3_MODELS}${GAZEBO_MODEL_PATH:+:${GAZEBO_MODEL_PATH}}"
  unset _TB3_MODELS _TB3_WORLDS
fi

export ASTROPATH_ROOT="${_ASTROPATH_ROOT}"
unset _ASTROPATH_ROOT

echo "[astropath env] TURTLEBOT3_MODEL=${TURTLEBOT3_MODEL}  ROS_DISTRO=${ROS_DISTRO:-?}  ASTROPATH_ROOT=${ASTROPATH_ROOT}"
