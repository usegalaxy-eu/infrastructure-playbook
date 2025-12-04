#!/bin/bash
# Description: This script will collect the usage of galaxy tools over time for the last month and output it in a format suitable for ingestion into the influxdb.
# Also the tool_id is cleaned up to remove the last part (such as version info) of the path and replace spaces with underscores.

gxadmin query q "COPY (
    SELECT date_trunc('month', create_time)::date AS month,
           REPLACE(regexp_replace(tool_id, '/[^/]+$', ''), ' ', '_') AS tool_id,
           COUNT(*) AS usage_count
    FROM job
    WHERE create_time >= date_trunc('month', NOW()) - INTERVAL '2 years'
    GROUP BY month, tool_id
) TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" \
| awk -F, '{printf "galaxy_tool_usage_over_time,tool_id=%s,month=%s usage_count=%d\n", $2, $1, $3}'
