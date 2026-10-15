#!/bin/bash
# Description: This script is used to get the number of active users in Galaxy for the previous month.

# Get the previous month in YYYY-MM format
prev_month=$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m)
year=$(echo "$prev_month" | cut -d- -f1)
month=$(echo "$prev_month" | cut -d- -f2)

# Query gxadmin and format output for InfluxDB
gxadmin csvquery monthly-users-active --year="$year" --month="$month" |  awk -F',' '{ printf "galaxy_monthly_active_users,month=%s active_users=%s\n", $1, $2 }'
