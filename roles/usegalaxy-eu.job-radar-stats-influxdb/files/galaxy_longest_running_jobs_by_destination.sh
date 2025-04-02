#!/bin/bash
# Description: This script uses gxadmin to get the longest running jobs on the Galaxy server and outputs the longest running jobs by destination in InfluxDB line protocol format.

gxadmin query q "COPY (SELECT j.id, regexp_replace(j.tool_id, '/[^/]+$', '') AS tool_id, j.destination_id, EXTRACT(EPOCH FROM (NOW() - jsh.running_since)) / 3600 AS hours_since_running FROM job j JOIN LATERAL (SELECT MIN(create_time) AS running_since FROM job_state_history jsh WHERE jsh.job_id = j.id AND jsh.state = 'running') jsh ON true WHERE j.state = 'running' ORDER BY hours_since_running DESC) TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" | awk -F, '{printf "longest_running_jobs,job_id=%s,tool_id=%s,destination_id=%s hours_since_running=%d\n", $1, $2, $3, $4}'
