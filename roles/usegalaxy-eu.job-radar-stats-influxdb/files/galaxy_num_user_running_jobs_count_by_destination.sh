#!/bin/bash
# Description: This script uses gxadmin to get the number of user jobs in the running state on the Galaxy server and outputs the number of user jobs by destination in InfluxDB line protocol format.

gxadmin query q "COPY (SELECT user_id, destination_id, COUNT(*) FROM job WHERE state = 'running' GROUP BY user_id, destination_id) TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" | awk -F',' '{uid=($1 == "" ? "00000" : $1); print "num_user_running_jobs_by_destination,destination_id="$2",user_id="uid" count="$3}'
