#!/bin/sh
set -eu

OLD="/root/allowed-cidrs.txt.old"
NOW="/root/allowed-cidrs.txt"
NEW="/root/allowed-cidrs.txt.new"

# Germany IP ranges
# 2026-11-19: (Renato) IP Deny ranges replaced by ipverse geo-ip as some German IPs were being left out and hence blocked (e.g. https://lens.ipverse.net/185.175.196.9)
# IP_RANGES="https://www.ipdeny.com/ipblocks/data/aggregated/de-aggregated.zone"
IP_RANGES="https://raw.githubusercontent.com/ipverse/geo-ip-blocks/refs/heads/master/country/de/de-ipv4.txt"

wget --quiet "$IP_RANGES" -O "$NEW"

if grep '^194.94' "$NEW" > /dev/null ; then
    [ -f "$NOW" ] && mv -f "$NOW" "$OLD"
    mv -f "$NEW" "$NOW"
else
    echo "Expected IP range not found. Keeping previous ranges file"
fi
