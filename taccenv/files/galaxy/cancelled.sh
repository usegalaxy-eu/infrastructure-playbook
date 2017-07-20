#!/bin/bash

# e.g. `cancelled.sh "1 week ago"`
[ -z "$1" ] && echo "usage: $0 <start-date>" && exit 1

ymd=`date +%Y-%m-%d --date "$1"`

sacct -u g2main -L -s CA -S $ymd -o 'jobname%-128' -X -n | sed 's/^pulsar_//' | cut -d_ -f1 | tr -d '^g' | (echo -n "select count(tool_id) ct, tool_id from job where id in("; while read jobid; do [[ $jobid =~ ^-?[0-9]+$ ]] && echo -n "$c$jobid"; c=','; done; echo ") and state='error' group by tool_id order by ct desc") | psql galaxy_main
