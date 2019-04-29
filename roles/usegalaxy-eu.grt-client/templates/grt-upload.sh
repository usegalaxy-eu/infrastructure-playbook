#!/bin/bash

# Prevent duplicate processes
pgrep -f 'scripts/grt/upload.py' && echo 'Previous GRT upload still running' && exit

start=$(date +%s)
python scripts/grt/upload.py \
	--report-directory {{ galaxy_mutable_data_dir }}/reports/ \
	--grt-config {{ glaxy_config_dir }}/grt.yml \
	--loglevel info
ec=$?
end=$(date +%s)

{% if gxadmin_influx_task_notifier is defined %}
runtime=$((start - end))
gxadmin meta influx-post {{ gxadmin_influx_task_notifier_db }} <(echo "grt-upload,host=$HOST code=$ec,runtime=$runtime $(date +%s%N)")
{% endif %}
