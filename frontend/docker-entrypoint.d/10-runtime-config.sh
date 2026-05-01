#!/bin/sh
set -eu

bool_env() {
  value="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    true|1|yes) printf 'true' ;;
    *) printf 'false' ;;
  esac
}

cat > /usr/share/nginx/html/runtime-config.js <<EOF
window.__ROUNDS_CONFIG__ = {
  VITE_DISABLE_SIGNUPS: "$(bool_env "${VITE_DISABLE_SIGNUPS:-false}")",
  VITE_OAUTH_GOOGLE_ENABLED: "$(bool_env "${VITE_OAUTH_GOOGLE_ENABLED:-false}")",
  VITE_OAUTH_GITHUB_ENABLED: "$(bool_env "${VITE_OAUTH_GITHUB_ENABLED:-false}")"
};
EOF
