#!/bin/sh
set -eu

bool_env() {
  value="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  case "$value" in
    true|1|yes) printf 'true' ;;
    *) printf 'false' ;;
  esac
}

# "NAME value" for every ROUNDS_GATE_* variable that is set, so the SPA
# reads the same gates as the runner and PocketBase. Gate values are
# lowercase words; anything else goes out as "invalid", which the SPA
# resolves to the gate's most restrictive value. Unset or empty gates
# are left out, and the SPA uses their written defaults.
gate_pairs() {
  env | sort | while IFS='=' read -r name value; do
    case "$name" in
      ROUNDS_GATE_*) ;;
      *) continue ;;
    esac
    case "$name" in
      *[!A-Z0-9_]*) continue ;;
    esac
    value="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]' | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
    [ -n "$value" ] || continue
    case "$value" in
      *[!a-z_]*) value=invalid ;;
    esac
    printf '%s %s\n' "$name" "$value"
  done
}

gates="$(gate_pairs)"
target="${ROUNDS_RUNTIME_CONFIG_PATH:-/usr/share/nginx/html/runtime-config.js}"

{
  printf 'window.__ROUNDS_CONFIG__ = {\n'
  printf '  VITE_DISABLE_SIGNUPS: "%s",\n' "$(bool_env "${VITE_DISABLE_SIGNUPS:-false}")"
  printf '  VITE_OAUTH_GOOGLE_ENABLED: "%s",\n' "$(bool_env "${VITE_OAUTH_GOOGLE_ENABLED:-false}")"
  printf '  VITE_OAUTH_GITHUB_ENABLED: "%s",\n' "$(bool_env "${VITE_OAUTH_GITHUB_ENABLED:-false}")"
  printf '%s\n' "$gates" | while read -r name value; do
    if [ -n "$name" ]; then
      printf '  %s: "%s",\n' "$name" "$value"
    fi
  done
  printf '};\n'
} > "$target"

# Startup log: every gate value passed to the SPA.
if [ -n "$gates" ]; then
  printf '%s\n' "$gates" | while read -r name value; do
    printf 'runtime-config: %s=%s\n' "$name" "$value"
  done
else
  printf 'runtime-config: no ROUNDS_GATE_* set, so the SPA uses each default\n'
fi
