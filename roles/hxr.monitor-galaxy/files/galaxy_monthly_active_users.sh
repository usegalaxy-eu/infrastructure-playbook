#!/bin/bash
# Description: This script is used to get the number of active users in Galaxy for the previous month.

# Run the script on the 1st of every month (since Telegraf does not support something like that in the config, I am using a check here and the interval will be set to 24h)
if [ "$(date +%d)" -ne 1 ]; then
    exit 0
fi

# Get the previous month in YYYY-MM format
prev_month=$(date -d "$(date +%Y-%m-01) -1 month" +%Y-%m)
year=$(echo "$prev_month" | cut -d- -f1)
month=$(echo "$prev_month" | cut -d- -f2)

# Query gxadmin and format output for InfluxDB
gxadmin csvquery monthly-users-active --year="$year" --month="$month" |  awk -F',' '{ printf "galaxy_monthly_active_users,month=%s active_users=%s\n", $1, $2 }'
