#!/bin/bash
# Description: This script will collect the usage of galaxy tools and formats the output to influxdb line protocol

gxadmin query user-tool-usage | \
tail -n +3 | \
awk -F'|' '
{
    # Extract and trim fields
    tool_name=$1
    count=$2

    gsub(/^[ \t]+|[ \t]+$/, "", tool_name)
    gsub(/^[ \t]+|[ \t]+$/, "", count)

    # Skip empty lines
    if (tool_name == "" || count == "") next

    # Escape spaces, commas, and equals for Influx tag safety
    gsub(/ /, "\\ ", tool_name)
    gsub(/,/, "\\,", tool_name)
    gsub(/=/, "\\=", tool_name)

    # Print in Influx line protocol format
    print "user_tool_usage,tool_name=" tool_name " count=" count " " systime() "000000000"
}'
