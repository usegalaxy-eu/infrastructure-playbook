#!/bin/bash
. {{ tiaas_dir }}/venv/bin/activate
cd {{ tiaas_dir }}/code/
export CONFIG_PATH="{{ tiaas_dir }}/config/config.yaml"
exec gunicorn --workers {{ tiaas_workers | default("4") }} --bind {{ tiaas_listen_url }} app:app
