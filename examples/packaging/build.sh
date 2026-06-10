#!/usr/bin/env bash
# build.sh — Package an Artic module directory into .amod archive
# Usage: ./build.sh <module-directory>
# Example: ./build.sh emotion-detect-v1.0.0
set -euo pipefail

MODULE_DIR="${1:-}"
if [ -z "$MODULE_DIR" ]; then
    echo "Usage: $0 <module-directory>"
    echo "Example: $0 emotion-detect-v1.0.0"
    exit 1
fi

if [ ! -f "$MODULE_DIR/manifest.toml" ]; then
    echo "Error: $MODULE_DIR/manifest.toml not found"
    exit 1
fi

# Extract version from manifest
VERSION=$(grep '^version' "$MODULE_DIR/manifest.toml" | head -1 | sed 's/.*"\(.*\)".*/\1/')
MODULE_NAME=$(grep '^id' "$MODULE_DIR/manifest.toml" | head -1 | sed 's/.*"\(.*\)".*/\1/' | tr '.' '-')
OUTPUT="${MODULE_NAME}-${VERSION}.amod"

echo "📦 Packaging $MODULE_DIR → $OUTPUT"
tar -czf "$OUTPUT" "$MODULE_DIR"
echo "✅ Done: $(ls -lh "$OUTPUT" | awk '{print $5}')"
