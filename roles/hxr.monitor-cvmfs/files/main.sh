#!/bin/bash
for repo in $(find /etc/cvmfs/repositories.d/ -mindepth 1 -maxdepth 1 -type d | cut -f5 -d/); do
	http_code=$(curl http://localhost/cvmfs/$repo/.cvmfspublished -I --silent | head -n 1 | cut -f2 -d' ')
	if [ "$http_code" -eq "200" ]; then
		echo "cvmfs.status,repo=$repo value=1"
	else
		echo "cvmfs.status,repo=$repo value=0"
	fi
done
