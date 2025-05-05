#!/bin/bash
# Description: This script retrieves the count of distinct user object sources, grouped by template ID, that are currently in use within the Galaxy instance.

gxadmin query q "COPY (select template_id, count(*) as user_count from user_object_store GROUP BY template_id) TO STDOUT WITH (FORMAT CSV, HEADER FALSE, DELIMITER ',');" | awk -F, '{printf "user_object_store_utilisation,template_id=%s user_count=%d\n", $1, $2}'
