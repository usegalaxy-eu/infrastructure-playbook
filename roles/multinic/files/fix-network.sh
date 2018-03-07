#!/usr/bin/env bash
ip route replace default via 192.52.2.254 dev eth0 2> /dev/null || true
ip route add 132.230.68.0/24 via 10.5.68.1 dev eth1 2> /dev/null || true
