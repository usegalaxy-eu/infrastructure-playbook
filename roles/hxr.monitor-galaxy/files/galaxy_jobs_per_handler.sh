#!/bin/bash
# Description: This script is used to get the number of jobs handled by each job handler in the current Galaxy job queue.

jobs_per_handler=$(/usr/bin/gxadmin gxadmin csvquery q "select handler, state, count(state) from job where state in ('new', 'queued', 'running') and handler like '%handler_sn06_%' group by handler, state order by handler")
echo "$jobs_per_handler" | awk -F, '{print "galaxy_jobs_per_handler_stats,handler="$1",state="$2" value="$3}'