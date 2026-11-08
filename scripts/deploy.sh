#!/usr/bin/env bash
# Build and deploy the static site to Cloudflare Pages (Direct Upload).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 scripts/build.py
python3 scripts/blake3.py

export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-09c58146832fbea01ce12d3e316a1d4d}"
export CLOUDFLARE_PAGES_PROJECT="${CLOUDFLARE_PAGES_PROJECT:-lingxifox-apps}"

python3 scripts/deploy_pages.py \
  --dist dist \
  --project "${CLOUDFLARE_PAGES_PROJECT}" \
  --branch main \
  --commit-dirty
