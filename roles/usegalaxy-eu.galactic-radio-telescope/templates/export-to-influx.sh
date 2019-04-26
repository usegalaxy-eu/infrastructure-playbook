#!/bin/bash
cd $(mktemp -d)

# Env vars for sending data
export PGHOST="/var/run/postgresql" PGUSER="{{ grt_user }}" PGNAME="{{ grt_user }}" PGPORT="" PGPASSWORD=""
export INFLUX_PASS={{ influxdb.node.password }}
export INFLUX_USER={{ influxdb.node.username }}
export INFLUX_URL={{ influxdb.url }}

# Export data into a file
./gxadmin meta iquery-grt-export > main.iflx

# Split into reasonable sized chunks
split --lines 10000 main.iflx SPLIT

# Clear out previous data points
gxadmin meta influx-query grt 'delete from "iquery-grt-export"'

# Send chunks to influxdb
for chunk in SPLIT*; do
	./gxadmin meta influx-post grt $chunk
done
