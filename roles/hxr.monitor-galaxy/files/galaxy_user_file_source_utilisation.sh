#!/bin/bash
# Description: This script retrieves the count of configured user file sources, grouped by template ID, that are currently in use within the Galaxy instance.

gxadmin query q "COPY (SELECT template_id, count(*) AS user_count FROM user_file_source WHERE active=true AND purged=false GROUP BY template_id) TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" | awk -F, '{printf "user_file_source_utilisation,template_id=%s user_count=%d\n", $1, $2}'
