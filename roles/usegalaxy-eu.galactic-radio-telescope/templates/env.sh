#!/bin/bash
export DJANGO_SETTINGS_MODULE=base.production
export DJANGO_ALLOWED_HOSTS="{{ grt_allowed_hosts }}"
export GRT_UPLOAD_DIR={{ grt_upload_dir }}
export PGHOST="{{ grt_pghost }}" PGUSER="{{ grt_pguser }}" PGNAME="{{ grt_pgname }}" PGPORT="{{ grt_pgport }}" PGPASSWORD="{{ grt_pgpassword }}"
