#!/usr/bin/env bash
set -eu

INTERFACE="eth0"
CIDR_FILE="/root/allowed-cidrs.txt"
IPSET="allowed-cidrs"
ALLOW_ZONE="allowed"
DROP_ZONE="drop"

[ ! -f "$CIDR_FILE" ] && /root/bin/fetch-ipranges.sh
[ ! -f "$CIDR_FILE" ] && echo "Failed to download IP ranges" && exit 1

# Remove IP set to be recreated later
firewall-cmd --permanent \
    --delete-ipset="allowed-cidrs"

# Create IP set
firewall-cmd --permanent \
    --new-ipset="$IPSET" \
    --type=hash:net

# Replace IP set contents
firewall-cmd --permanent \
    --ipset="$IPSET" \
    --remove-entries-from-file="$CIDR_FILE"

firewall-cmd --permanent \
    --ipset="$IPSET" \
    --add-entries-from-file="$CIDR_FILE"

# Create accepting zone for allowed CIDRs
firewall-cmd --permanent \
    --new-zone="$ALLOW_ZONE" || true

firewall-cmd --permanent \
    --zone="$ALLOW_ZONE" \
    --set-target=ACCEPT

firewall-cmd --permanent \
    --zone="$ALLOW_ZONE" \
    --add-source="ipset:$IPSET"

# Drop everything else on the interface
firewall-cmd --permanent \
    --zone="$DROP_ZONE" \
    --change-interface="$INTERFACE"

firewall-cmd --reload
