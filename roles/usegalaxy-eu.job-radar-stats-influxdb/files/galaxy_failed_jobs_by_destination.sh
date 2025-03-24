#!/bin/bash
# Description: This script uses gxadmin to get the errored jobs from the Galaxy server in the last 1 hour and outputs the count of errored jobs by destination in InfluxDB line protocol format.

gxadmin tsvquery errored-jobs 1 | awk '{count[$7]++} END {for (dest in count) printf "errored_jobs_by_destination,destination_id=%s,state=errored count=%d\n", dest, count[dest]}'
