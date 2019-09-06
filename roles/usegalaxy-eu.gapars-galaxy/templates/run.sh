#!/bin/bash
. {{ gapars_dir }}/venv/bin/activate
cd {{ gapars_dir }}/code/
export CONFIG_PATH="{{ gapars_dir }}/config/config.yaml"
export PYTHONUNBUFFERED=1
exec gunicorn --workers {{ gapars_workers | default("4") }} --bind {{ gapars_listen_url }} app:app
