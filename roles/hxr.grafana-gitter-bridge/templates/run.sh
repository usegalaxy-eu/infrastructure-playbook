#!/bin/bash
. {{ ggb_dir }}/venv/bin/activate
cd {{ ggb_dir }}/code/
export CONFIG_PATH="{{ ggb_dir }}/config/config.yaml"
exec gunicorn --workers {{ ggb_workers | default("4") }} --bind {{ ggb_listen_url | default("127.0.0.1:5000") }} app:app
