#!/bin/bash
check_repo() {
	host="$1"
	repo="$2"

	http_code="$(curl http://$host/cvmfs/$repo/.cvmfspublished -I --silent | head -n 1 | cut -f2 -d' ')"
	header="$(curl http://$host/cvmfs/$repo/.cvmfspublished --silent | head -n 12)"

	if [ "$http_code" -eq "200" ]; then
		size=$(echo "$header" | grep '^B' | cut -c2-)
		gc=$(echo "$header" | grep '^G' | cut -c2- | sed 's/yes/t;s/no/f;')
		ts=$(echo "$header" | grep '^T' | cut -c2-)
		rev=$(echo "$header" | grep '^S' | cut -c2-)

		echo "cvmfs.status,host=$host,repo=$repo value=1,size=$size,gc=$gc,ts=$ts,rev=$rev"
	else
		echo "cvmfs.status,host=$host,repo=$repo value=0"
	fi
}

{% for host in cvmfs_check_servers.hosts %}
{% for repo in cvmfs_check_servers.repos %}
check_repo {{ host }} {{ repo }}
{% endfor %}
{% endfor %}
