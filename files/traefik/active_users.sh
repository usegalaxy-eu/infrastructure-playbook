#!/bin/bash

cu=$(awk -vDate=`date -u -d'now-10 minutes' +[%d/%b/%Y:%H:%M:%S` '$4 > Date {print $0}' /var/log/traefik/access.log | grep "/history/current_history_json"  | awk "{print \$1}" | sort -u | wc -l)

echo "active_users,timespan=last_10_min users=$cu"
