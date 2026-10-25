#!/usr/bin/env bash
# Save the live /map topic to astropath_config/maps/school_floor.{pgm,yaml}
#
# Prefers nav2_map_server map_saver_cli (occupancy grid from slam_toolbox).
# Requires: mapping stack running with use_sim_time:=true and a non-empty /map.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/env.sh"

ROOT="${ASTROPATH_ROOT:-$(cd "${SCRIPT_DIR}/.." && pwd)}"
OUT_DIR="${ROOT}/ros2_ws/src/astropath_config/maps"
MAP_STEM="${OUT_DIR}/school_floor"
PREVIEW="${ROOT}/docs/images/school_floor_map.png"

mkdir -p "${OUT_DIR}" "${ROOT}/docs/images"

echo "[save_map] Waiting for /map publisher (use_sim_time)…"
READY=0
for _ in $(seq 1 90); do
  info="$(ros2 topic info /map 2>/dev/null || true)"
  if echo "${info}" | grep -E 'Publisher count:[[:space:]]*[1-9]' >/dev/null; then
    READY=1
    break
  fi
  sleep 1
done
if [[ "${READY}" -ne 1 ]]; then
  echo "[save_map] ERROR: /map has no publisher — is SLAM running?" >&2
  exit 1
fi

echo "[save_map] Saving via nav2_map_server map_saver_cli -> ${MAP_STEM}"
# Preferred path: occupancy grid from slam_toolbox /map topic.
# (slam_toolbox /slam_toolbox/save_map also works but writes via its own naming.)
ros2 run nav2_map_server map_saver_cli \
  -f "${MAP_STEM}" \
  --ros-args -p use_sim_time:=true

if [[ ! -f "${MAP_STEM}.pgm" || ! -f "${MAP_STEM}.yaml" ]]; then
  echo "[save_map] ERROR: expected ${MAP_STEM}.pgm and .yaml" >&2
  exit 1
fi

# Normalize yaml image field to basename (map_saver may write absolute/stem path)
python3 - "${MAP_STEM}.yaml" <<'PY'
from pathlib import Path
import sys
yp = Path(sys.argv[1])
lines = []
for line in yp.read_text().splitlines():
    if line.startswith('image:'):
        lines.append('image: school_floor.pgm')
    else:
        lines.append(line)
yp.write_text('\n'.join(lines) + '\n')
print(f'[save_map] Normalized {yp}')
PY

# Preview PNG from PGM (Pillow / PIL if available, else convert/ffmpeg fallback)
python3 - <<'PY' "${MAP_STEM}.pgm" "${PREVIEW}"
import sys
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
try:
    from PIL import Image
    img = Image.open(src)
    img.save(dst)
    print(f"[save_map] Wrote preview {dst} size={img.size}")
except Exception as e:
    # Fallback: copy raw via shutil after trying imageio/cv2
    try:
        import cv2
        im = cv2.imread(str(src), cv2.IMREAD_UNCHANGED)
        if im is None:
            raise RuntimeError('cv2 failed to read pgm')
        cv2.imwrite(str(dst), im)
        print(f"[save_map] Wrote preview {dst} via cv2 shape={im.shape}")
    except Exception as e2:
        print(f"[save_map] WARN: could not write PNG preview ({e}; {e2})", file=sys.stderr)
        sys.exit(0)
PY

echo "[save_map] OK: ${MAP_STEM}.yaml"
ls -la "${MAP_STEM}.pgm" "${MAP_STEM}.yaml" "${PREVIEW}" 2>/dev/null || true
