#!/bin/sh
##
## This file is maintained by Ansible - CHANGES WILL BE OVERWRITTEN
##
set -e

{% for item in galaxy_pgcleanup_objectstores | default([]) %}
{{ galaxy_venv_dir }}/bin/python {{ galaxy_server_dir }}/scripts/cleanup_datasets/pgcleanup.py -c {{ galaxy_config_file }} -o {{ item.days }} -l {{ galaxy_log_dir }} -w 128MB --object-store-id {{ item.objectstore_id }} purge_old_hdas 2>&1 | tee -a {{ galaxy_log_dir }}/cleanup_objectstore_datasets.log
{% endfor %}
