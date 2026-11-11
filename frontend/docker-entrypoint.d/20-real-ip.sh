#!/bin/sh
set -eu

# The client address nginx counts and forwards (ROUNDS-00B-L04). Behind
# anything in front of nginx, a front proxy, a tunnel, or the k8s ingress
# controller, compose included, set ROUNDS_FRONTEND_REAL_IP_FROM to the
# addresses it connects from (comma-separated CIDRs or addresses), and have
# it send each client's address in X-Forwarded-For. nginx then takes that
# address, past those proxies, for the share resolver's backstop and the
# X-Real-IP it sends the runner. Unset or empty, nginx uses the peer's
# address, which is right only where its own port is the public one. An
# entry that isn't an address or a CIDR stops the container, so a typo
# never trusts the wrong hop.

target="${ROUNDS_REAL_IP_CONF_PATH:-/etc/nginx/conf.d/00-real-ip.conf}"
raw="${ROUNDS_FRONTEND_REAL_IP_FROM:-}"

if [ -z "$(printf '%s' "$raw" | tr -d ', \t')" ]; then
  rm -f "$target"
  printf 'real-ip: ROUNDS_FRONTEND_REAL_IP_FROM is unset, so nginx counts each client by its peer address\n'
  exit 0
fi

lines=""
count=0
for item in $(printf '%s' "$raw" | tr ',' ' '); do
  case "$item" in
    *[!0-9A-Fa-f:./]* | */*/* | /* | */)
      printf 'real-ip: ROUNDS_FRONTEND_REAL_IP_FROM has an entry that is not an address or a CIDR\n' >&2
      exit 1
      ;;
  esac
  lines="${lines}set_real_ip_from ${item};
"
  count=$((count + 1))
done

{
  printf '# Written at start by 20-real-ip.sh from ROUNDS_FRONTEND_REAL_IP_FROM.\n'
  printf '%s' "$lines"
  printf 'real_ip_header X-Forwarded-For;\n'
  printf 'real_ip_recursive on;\n'
} > "$target"
printf 'real-ip: nginx takes the client address from X-Forwarded-For past %s trusted entries\n' "$count"
