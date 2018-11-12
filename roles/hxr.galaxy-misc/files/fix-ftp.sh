#!/bin/bash
. /opt/galaxy/.bashrc
for username in $(psql -c 'COPY (select email from galaxy_user) TO STDOUT WITH CSV'); do
	mkdir -p "/data/0/incoming/$username"
done;
