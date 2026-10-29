#!/usr/bin/env sh
# Assemble a ready-to-upload Hugging Face Space in dist/space from the backend.
#   sh deploy/huggingface-space/build_space.sh
#   hf upload <user>/mijhar dist/space . --repo-type space     (or drag the folder's files into the Space's "Files" tab)
set -e
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT="$ROOT/dist/space"
rm -rf "$OUT" && mkdir -p "$OUT"
cp "$ROOT/backend/pyproject.toml" "$ROOT/backend/uv.lock" "$OUT/"
cp -r "$ROOT/backend/mijhar" "$OUT/mijhar"
find "$OUT" -name __pycache__ -type d -prune -exec rm -rf {} +
cp "$ROOT/deploy/huggingface-space/Dockerfile.space" "$OUT/Dockerfile"
cp "$ROOT/deploy/huggingface-space/README.space.md" "$OUT/README.md"
echo "Space ready in $OUT"
