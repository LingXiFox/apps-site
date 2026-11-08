#!/usr/bin/env bash
# Build and deploy the static site to Cloudflare Pages (Direct Upload).
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

python3 scripts/build.py

export CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-09c58146832fbea01ce12d3e316a1d4d}"

if [[ -z "${CLOUDFLARE_API_TOKEN:-}" ]]; then
  if ! npx wrangler whoami >/dev/null 2>&1; then
    echo "Wrangler is not authenticated. Run 'npx wrangler login' or export CLOUDFLARE_API_TOKEN." >&2
    exit 1
  fi
fi

npx wrangler pages deploy dist \
  --project-name lingxifox-apps \
  --branch main \
  --commit-dirty=true
