#!/bin/bash
. /opt/galaxy/.bashrc

stat_timeout=0.1 # seconds
nfs_mp="/data/0"

timeout -s kill $stat_timeout stat -t $nfs_mp > /dev/null
if [[ ! $? == 137 ]];  then
	for username in $(psql -c 'COPY (select email from galaxy_user) TO STDOUT WITH CSV'); do
		mkdir -p "$nfs_mp/incoming/$username"
	done;
fi
