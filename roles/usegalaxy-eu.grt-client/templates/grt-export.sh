#!/bin/bash

# Prevent duplicate processes
pgrep -f 'scripts/grt/export.py' && echo 'Previous GRT export still running' && exit

# Otherwise start the export
start=$(date +%s)
python scripts/grt/export.py \
	--report-directory {{ galaxy_mutable_data_dir }}/reports/ \
	--grt-config {{ galaxy_config_dir }}/grt.yml \
	--config-file {{ galaxy_config_dir }}/{{ galaxy_config_file_basename }} \
	--loglevel info \
	--batch-size 10000
ec=$?
end=$(date +%s)

{% if gxadmin_influx_task_notifier is defined %}
runtime=$((start - end))
gxadmin meta influx-post {{ gxadmin_influx_task_notifier_db }} <(echo "grt-export,host=$HOST code=$ec,runtime=$runtime $(date +%s%N)")
{% endif %}
