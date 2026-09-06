#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
freecad_bin=${FREECAD_BIN:-/Applications/FreeCAD.app/Contents/MacOS/FreeCAD}
if [ ! -x "$freecad_bin" ]; then
  printf '%s\n' 'Set FREECAD_BIN to your FreeCAD executable (tested version: 1.1.3).' >&2
  exit 1
fi
export CADCOPILOT_ROOT="$project_root"
exec "$freecad_bin" "$project_root/freecad/StartCopilot.FCMacro"
