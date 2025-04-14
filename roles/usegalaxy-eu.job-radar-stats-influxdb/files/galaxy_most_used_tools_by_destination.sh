#!/bin/bash
# Description: This script uses gxadmin to count the most used tools on the Galaxy server and outputs the count of most used tools by destination in InfluxDB line protocol format.

gxadmin query q "COPY (SELECT regexp_replace(tool_id, '/[^/]+$', '') AS tool_id_no_version, destination_id, COUNT(*) AS job_count FROM job WHERE create_time >= (now() AT TIME ZONE 'UTC' - INTERVAL '1 hours') AND tool_id ILIKE 'toolshed%' AND destination_id IS NOT NULL GROUP BY tool_id_no_version, destination_id ORDER BY job_count DESC) TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" | awk -F, '{gsub(/ /, "_", $1); printf "most_used_tools_by_destination,tool_id=%s,destination_id=%s job_count=%d\n", $1, $2, $3}'
