#!/bin/bash
export DJANGO_SETTINGS_MODULE=base.production
export DJANGO_ALLOWED_HOSTS="telescope.galaxyproject.eu"
export GRT_UPLOAD_DIR={{ grt_upload_dir }}
export PGHOST="/var/run/postgresql" PGUSER="{{ grt_user }}" PGNAME="{{ grt_user }}" PGPORT="" PGPASSWORD=""
