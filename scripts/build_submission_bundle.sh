#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bundle_name="fundamental_ai_crypto_volatile"
out_dir="$repo_root/submission"
out_zip="$out_dir/${bundle_name}.zip"
stage_dir="$(mktemp -d)"
bundle_root="$stage_dir/$bundle_name"

cleanup() {
  rm -rf "$stage_dir"
}
trap cleanup EXIT

mkdir -p "$bundle_root"

copy_paths=(
  ".env.example"
  ".github"
  ".gitignore"
  "CONTRIBUTING.md"
  "Makefile"
  "README.md"
  "compose.yaml"
  "config.yaml"
  "dashboard"
  "data/processed"
  "docker"
  "docs"
  "features"
  "img"
  "models"
  "notebooks"
  "pipeline"
  "reports"
  "requirements-dev.txt"
  "requirements.txt"
  "pyproject.toml"
  "scripts"
  "service"
  "templates"
  "tests"
)

for rel_path in "${copy_paths[@]}"; do
  dest_path="$bundle_root/$rel_path"
  mkdir -p "$(dirname "$dest_path")"
  cp -R "$repo_root/$rel_path" "$dest_path"
done

rm -rf "$bundle_root/reports/build"
rm -rf "$bundle_root/models/artifacts/1"
rm -f "$bundle_root/data/processed/features_modelcheck.parquet"
find "$bundle_root" -name '.DS_Store' -delete
find "$bundle_root" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$bundle_root" -name '*.pyc' -delete

rm -f "$out_zip"
(
  cd "$stage_dir"
  zip -qr "$out_zip" "$bundle_name"
)

printf 'Wrote %s\n' "$out_zip"
