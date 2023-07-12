#!/bin/bash
# Description: This script is used to get the number of jobs in each state in the Galaxy job queue.
job_state_stats=$(/usr/bin/gxadmin tsvquery queue-detail --all | awk '{print $1}' | sort | uniq -c)
echo "$job_state_stats" | awk '{print "galaxy_job_queue_states_stats,job_state="$2" value="$1}'