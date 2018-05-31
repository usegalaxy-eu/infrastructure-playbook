#!/usr/bin/env bash
ip route add 10.4.7.0/24     via 10.5.68.1 dev eth1 2> /dev/null || true
#ip route add 132.230.68.0/24 via 10.5.68.1 dev eth1 2> /dev/null || true
