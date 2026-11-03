#!/bin/bash
# Description: This script will collect the usage of galaxy tools and formats the output to influxdb line protocol

gxadmin csvquery tool-usage | awk -F, '{split($1, a, "/"); if (length(a) > 1) {tool_id = a[length(a)-1]; version = a[length(a)]} else {tool_id = $1; version = "unknown"}; gsub(/ /, "\\ ", tool_id); gsub(/ /, "\\ ", version); print "tool-usage,tool_id=" tool_id ",version=" version " count=" $2 " " systime() "000000000"}'
