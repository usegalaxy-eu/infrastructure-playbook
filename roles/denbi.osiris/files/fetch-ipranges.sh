#!/bin/sh
set -eu

OLD="/root/allowed-cidrs.txt.old"
NOW="/root/allowed-cidrs.txt"
NEW="/root/allowed-cidrs.txt.new"

wget --quiet https://www.ipdeny.com/ipblocks/data/aggregated/de-aggregated.zone -O "$NEW"

if grep 194.94 "$NEW" > /dev/null ; then
    [ -f "$NOW" ] && mv -f "$NOW" "$OLD"
    mv -f "$NEW" "$NOW"
else
    echo "Expected IP range not found. Keeping previous ranges file"
fi
