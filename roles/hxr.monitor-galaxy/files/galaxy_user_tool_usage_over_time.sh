#!/bin/bash
# Description: This script will collect the usage of galaxy tools over time for the last month and output it in a format suitable for ingestion into the influxdb.
# Also the tool_id is cleaned up to remove the last part (such as version info) of the path and replace spaces with underscores.

gxadmin query user-tool-usage-over-time | \
tail -n +4 | \
awk -F'|' '
{
    # Extract fields
    date=$1
    tool_name=$2
    count=$3

    # Trim whitespace
    gsub(/^[ \t]+|[ \t]+$/, "", date)
    gsub(/^[ \t]+|[ \t]+$/, "", tool_name)
    gsub(/^[ \t]+|[ \t]+$/, "", count)

    # Skip empty lines
    if (date == "" || tool_name == "" || count == "") next

    # Escape Influx tag characters
    gsub(/ /, "\\ ", tool_name)
    gsub(/,/, "\\,", tool_name)
    gsub(/=/, "\\=", tool_name)

    # Convert date (YYYY-MM-DD) to nanosecond timestamp
    cmd = "date -d \"" date "\" +%s"
    cmd | getline ts
    close(cmd)

    # Print Influx line protocol
    print "user_tool_usage_over_time,tool_name=" tool_name " count=" count " " ts "000000000"
}'
