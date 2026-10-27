#!/usr/bin/env bash
set -euo pipefail

# Build an Apache <Directory> snippet that only accepts client IPs
# listed in the allowed-CIDRs file then reloads httpd. Client IPs
# are retrieved from the X-Forwarded-For header by Apache's mod_remoteip
# (configured for each vhost).

readonly CIDR_FILE="/root/allowed-cidrs.txt"
readonly FETCH_CIDR="/root/bin/fetch-ipranges.sh"
readonly CONF_FILE="/etc/httpd/osiris-allowed-cidrs.conf"
readonly CACHE_DIR="/root/.cache"

: "${OSIRIS_WWW_DIR:?OSIRIS_WWW_DIR must be set (e.g. /var/www/osiris)}"

[[ -f "$CIDR_FILE" ]] || "$FETCH_CIDR"
[[ -f "$CIDR_FILE" ]] || { echo "Failed to download IP ranges"; exit 1; }

mkdir -p "$CACHE_DIR"

# Create a temporary file to build the IP allow-list in
TMP="$(mktemp -p "$CACHE_DIR" .apache-block.XXXXXX)"
chmod 600 "$TMP"
trap 'rm -f "$TMP"' EXIT INT TERM

# --- Parsing and validation of IP ranges ---
# Read CIDR lines, dropping blank lines and comments.
mapfile -t cidrs < <(sed 's/[[:blank:]]*#.*$//' "$CIDR_FILE" | grep -E -v '^[[:blank:]]*$')

# Every CIDR must be a valid IPv4 address (optionally /CIDR).
ipv4_re='^([0-9]{1,3}\.){3}[0-9]{1,3}(/[0-9]{1,2})?$'
bad=()
for cidr in "${cidrs[@]}"; do
    [[ "$cidr" =~ $ipv4_re ]] || bad+=("$cidr")
done
if (( ${#bad[@]} > 0 )); then
    echo "Allowlist contains malformed IP ranges:"
    printf '    %s\n' "${bad[@]}"
    exit 1
fi

# Write the Apache <Directory> directive to the file, deny all except
# the allowed CIDRs
{
    printf '<Directory "%s">\n' "$OSIRIS_WWW_DIR"
    printf '    Require all denied\n'
    if (( ${#cidrs[@]} > 0 )); then
        printf '    Require ip %s\n' "${cidrs[@]}"
    fi
    printf '</Directory>\n'
} > "$TMP"

# --- Deploy configuration file -----------------------------
# Record the previous config's mode/owner so the new file inherits
# them and back it up so changes can be rolled back if needed.
if [[ -f "$CONF_FILE" ]]; then
    conf_mode=$(stat -c '%a' "$CONF_FILE")
    conf_owner=$(stat -c '%u:%g' "$CONF_FILE")
    cp -p "$CONF_FILE" "${CONF_FILE}.bak"
else
    conf_mode=644
    conf_owner=0:0
fi

# Deploy configuration file
mv "$TMP" "$CONF_FILE"
chmod "$conf_mode" "$CONF_FILE"
chown "$conf_owner" "$CONF_FILE"

# Validate using `httpd -t` and roll-back if invalid
if ! /usr/sbin/httpd -t; then
    echo "httpd config validation failed; restoring previous config"
    if [[ -f "${CONF_FILE}.bak" ]]; then
        mv -f "${CONF_FILE}.bak" "$CONF_FILE"
    else
        rm -f "$CONF_FILE"
    fi
    exit 1
fi

rm -f "${CONF_FILE}.bak"
systemctl reload httpd
