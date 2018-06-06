#!/bin/bash
curl --silent http://localhost:3128/squid-internal-mgr/info | python /usr/bin/parse_squid.py
