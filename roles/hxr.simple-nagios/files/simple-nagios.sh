#! /bin/bash

expect_http() {
	service=$1
	url=$2
	expected_status=$3

	t_start=$(date +%s.%N)
	response_code=$(curl 2>/dev/null --silent --connect-timeout 30 $url -I | head -n1 | awk '{print $2}');
	t_end=$(date +%s.%N)
	t_delta=$(echo "$t_end - $t_start" | bc -l)

	if [[ $response_code -eq $expected_status ]]; then
		status=0
	else
		status=1
	fi
	echo "$service code=$response_code,time=$t_delta,status=$status"
}


expect_http eu.usegalaxy.pages.home_nossl http://usegalaxy.eu 301
expect_http eu.usegalaxy.pages.home https://usegalaxy.eu 200
expect_http eu.usegalaxy.pages.hicexplorer https://hicexplorer.usegalaxy.eu 200

expect_http eu.usegalaxy.pages.stats https://stats.usegalaxy.eu 200
expect_http eu.usegalaxy.pages.stats https://stats.usegalaxy.eu 200

expect_http eu.usegalaxy.pages.grt https://telescope.galaxyproject.org/ 200
expect_http eu.usegalaxy.pages.grt_api https://telescope.galaxyproject.org/api/instance/top_all.json 200
expect_http eu.usegalaxy.pages.grt_login https://telescope.galaxyproject.org/grt-admin/accounts/login/ 200

expect_http eu.usegalaxy.pages.build https://build.usegalaxy.eu/ 200

expect_http eu.usegalaxy.pages.sql https://sql.usegalaxy.eu/login/ 200
expect_http eu.usegalaxy.pages.csp https://csp.usegalaxy.eu/ 200
expect_http eu.usegalaxy.pages.git https://gitlab.denbi.uni-freiburg.de/users/sign_in 200
expect_http eu.usegalaxy.pages.ftp_docs https://ftp.usegalaxy.eu/ 200

expect_http eu.usegalaxy.pages.influx http://influxdb.denbi.uni-freiburg.de:8086/ping 204
expect_http eu.usegalaxy.pages.sentry https://sentry.denbi.uni-freiburg.de/auth/login/sentry/ 200
