#!/usr/bin/env bash
# Copies the website's assets from the sibling repositories into site/:
# the case STLs (brewberrypi-case) and the example recipe (brewberrypi-app).
#
#   tools/sync_assets.sh [path/containing/the/sibling/repos]
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
repos="${1:-$root/..}"
case_stl="$repos/brewberrypi-case/04-stl"
recipes="$repos/brewberrypi-app/docs/specification/data/recipes"

mkdir -p "$root/site/models" "$root/site/data"
for part in body divider top_lid bottom_lid; do
  cp "$case_stl/brewberrypi-case-$part.stl" "$root/site/models/case-$part.stl"
done
cp "$case_stl/previews/assembly-iso.png" "$root/site/img/case-assembly.png"
# The recipe of the hero curve and the recipe timeline.
cp "$recipes/BENIWEISS.json" "$root/site/data/recipe.json"
echo "copied the case STLs, its preview and the example recipe to site/"
