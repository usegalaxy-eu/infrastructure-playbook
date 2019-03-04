#!/bin/bash
#- DJANGO_SETTINGS_MODULE=base.production
. {{ grt_dir }}/config/env.sh
{{ grt_dir }}/venv/bin/uwsgi \
	--yml {{ grt_dir }}/config/uwsgi.yml
