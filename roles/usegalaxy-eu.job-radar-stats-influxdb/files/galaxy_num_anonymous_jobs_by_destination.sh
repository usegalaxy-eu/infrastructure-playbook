#!/bin/bash
# Description: This script uses gxadmin to count the number of jobs run by anonymous users on the Galaxy server and outputs the count of anonymous users by destination in InfluxDB line protocol format.

gxadmin csvquery queue-detail | awk -F',' '/Anonymous User/ {count[$9]++} END {for (id in count) print "anonymous_user_jobs_by_destination,destination_id=" id ", count=" count[id]}'
