#!/bin/bash
# Description: This script retrieves job metadata, resource usage metrics, and compute start and finish times from the Galaxy server using gxadmin and outputs the data in InfluxDB line protocol format.

# Set the time interval for the query
hours=4

# This query retrieves the job metadata
gxadmin query q "COPY (SELECT id AS job_id, EXTRACT(EPOCH FROM create_time)::BIGINT AS job_create_time, destination_id, tool_id FROM job WHERE state IN ('ok', 'error') AND update_time >= NOW() - INTERVAL '${hours} hour' AND tool_id != '__DATA_FETCH__') TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" | awk -F',' '{job_id = $1;job_create_time = $2;destination_id = $3;tool_id = $4;gsub(/[ ,=]/, "_", tool_id);printf"galaxy_job_metadata,job_id=%s,tool_id=%s,destination_id=%s job_create_time=%ds\n", job_id, tool_id, destination_id, job_create_time;}'

# This query retrieves the job resource and usage metrics
gxadmin query q "COPY (SELECT job_id, metric_name, metric_value FROM job_metric_numeric WHERE job_id IN (SELECT id FROM job WHERE state IN ('ok', 'error') AND update_time >= NOW() - INTERVAL '${hours} hour' AND tool_id != '__DATA_FETCH__') AND metric_name IN ('galaxy_slots', 'galaxy_memory_mb', 'memory.peak')) TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" | awk -F, '{printf "galaxy_job_metrics,job_id=%s metric_name=\"%s\",metric_value=%s\n", $1, $2, $3}'

# This query retrieves the jobs compute start time and final state time
gxadmin query q "COPY (SELECT job_id, EXTRACT(EPOCH FROM MIN(CASE WHEN state = 'running' THEN create_time END))::BIGINT AS running_start_time, EXTRACT(EPOCH FROM MAX(CASE WHEN state IN ('ok', 'error') THEN create_time END))::BIGINT AS final_state_time FROM job_state_history WHERE job_id IN (SELECT id FROM job WHERE state IN ('ok', 'error') AND update_time >= NOW() - INTERVAL '${hours} hour' AND tool_id != '__DATA_FETCH__') AND state IN ('running', 'ok', 'error') GROUP BY job_id) TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" | awk -F, '{printf "galaxy_job_state,job_id=%s running_start_time=%d final_state_time=%d\n", $1, $2, $3}'
