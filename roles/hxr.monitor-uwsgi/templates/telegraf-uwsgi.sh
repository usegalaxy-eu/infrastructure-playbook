#!/bin/bash
PATH=/opt/galaxy/venv/bin:/sbin:/bin:/usr/sbin:/usr/bin gxadmin uwsgi stats-influx 127.0.0.1:4010 2>/dev/null || true
PATH=/opt/galaxy/venv/bin:/sbin:/bin:/usr/sbin:/usr/bin gxadmin uwsgi stats-influx 127.0.0.1:4011 2>/dev/null || true
PATH=/opt/galaxy/venv/bin:/sbin:/bin:/usr/sbin:/usr/bin gxadmin uwsgi stats-influx 127.0.0.1:4012 2>/dev/null || true
PATH=/opt/galaxy/venv/bin:/sbin:/bin:/usr/sbin:/usr/bin gxadmin uwsgi stats-influx 127.0.0.1:4013 2>/dev/null || true
exit 0
