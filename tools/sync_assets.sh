#!/usr/bin/env bash
# Copies the website's assets from the sibling repositories into site/:
# the case STLs and the case render (brewberrypi-case).
#
#   tools/sync_assets.sh [path/containing/the/sibling/repos]
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
repos="${1:-$root/..}"
case_stl="$repos/brewberrypi-case/04-stl"

mkdir -p "$root/site/models"
for part in body divider top_lid bottom_lid; do
  cp "$case_stl/brewberrypi-case-$part.stl" "$root/site/models/case-$part.stl"
done
cp "$case_stl/previews/assembly-iso.png" "$root/site/img/case-assembly.png"
echo "copied the case STLs and its preview to site/"
