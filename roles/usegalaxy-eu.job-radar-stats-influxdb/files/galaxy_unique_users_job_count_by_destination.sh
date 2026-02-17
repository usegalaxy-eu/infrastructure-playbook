#!/bin/bash
# Description: This script uses gxadmin to count the unique users running jobs on the Galaxy server and outputs the count of unique users by destination in InfluxDB line protocol format.

gxadmin csvquery queue-detail | grep running | awk -F, '{users[$9][$5]=1} END {for (dest in users) {count=0; for (user in users[dest]) count++; printf "num_unique_users_jobs_by_destination,destination_id=%s,state=running unique_user_count=%d\n", dest, count}}'
