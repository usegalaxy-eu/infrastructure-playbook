#! /bin/bash
GALAXY_API_KEY=$(cat /etc/gx-api-creds.txt)

expect_http() {
	service=$1
	url=$2
	expected_status=$3

	t_start=$(date +%s.%N)
	response_code=$(timeout 10 curl 2>/dev/null --silent --connect-timeout 10 $url -I | head -n1 | awk '{print $2}');
	t_end=$(date +%s.%N)
	t_delta=$(echo "1000000 * ($t_end - $t_start)" | bc -l)
	t_delta=$(echo $t_delta | sed 's/\..*//')

	if [[ $response_code -eq $expected_status ]]; then
		status=0
	else
		status=1
	fi
	echo "eu.usegalaxy.pages,page=$service code=$response_code,request_time=0$t_delta,status=$status"
}

expect_ftps(){
	service=$1
	url=$2

	random=$RANDOM
	tmpfile=$(mktemp galaxy.nagios.XXXXXXXX --tmpdir)
	fromserver=$(mktemp galaxy.nagios.XXXXXXXX --tmpdir)

	echo $random > $tmpfile

	t_start=$(date +%s.%N)
	# Upload the file
	timeout 2 lftp $url <<EOF
login $(cat /etc/ftp-creds.txt)
set ftp:ssl-force true
set ftp:ssl-protect-data true
put $tmpfile -o nagios
exit
EOF

	# Remove the target file, lftp doesn't like to overwrite.
	rm -f $fromserver
	timeout 2 lftp $url <<EOF
login $(cat /etc/ftp-creds.txt)
set ftp:ssl-force true
set ftp:ssl-protect-data true
get nagios -o $fromserver
exit
EOF

	diff $tmpfile $fromserver
	exit_code=$?
	rm -f $tmpfile $fromserver

	t_end=$(date +%s.%N)
	t_delta=$(echo "1000000 * ($t_end - $t_start)" | bc -l)
	t_delta=$(echo $t_delta | sed 's/\..*//')

	echo "eu.usegalaxy.services,service=$service request_time=0$t_delta,status=$exit_code"

}

expect_gx_ftp_age() {
	service=$1
	url=$2
	t_start=$(date +%s.%N)
	# Fetch the timestamp from the remote_files api
	timestamp=$(curl --silent $url/api/remote_files?key=$GALAXY_API_KEY | jq '.[] | select(.path = "nagios") | .ctime' -r)
	# Parse the date
	created_at=$(date --date="$timestamp" "+%s")
	now=$(date "+%s")
	# Calculate its age.
	file_age=$(echo "$now - $created_at" | bc)

	t_end=$(date +%s.%N)
	t_delta=$(echo "1000000 * ($t_end - $t_start)" | bc -l)
	t_delta=$(echo $t_delta | sed 's/\..*//')

	# Allow the file to be up to 300 seconds (5 minutes) old
	if [[ $file_age -lt 300 ]]; then
		status=0
	else
		status=1
	fi

	echo "eu.usegalaxy.services,service=$service request_time=0$t_delta,status=$status"
}


expect_http home_nossl http://usegalaxy.eu 301
expect_http home https://usegalaxy.eu 200
expect_http hicexplorer https://hicexplorer.usegalaxy.eu 200

expect_http stats https://stats.usegalaxy.eu 200
expect_http stats https://stats.usegalaxy.eu 200
expect_http apollo https://apollo.usegalaxy.eu/annotator/index 200

expect_http grt https://telescope.galaxyproject.org/ 200
expect_http grt_api https://telescope.galaxyproject.org/api/instance/top_all.json 200
expect_http grt_login https://telescope.galaxyproject.org/grt-admin/accounts/login/ 200

expect_http build https://build.usegalaxy.eu/ 200

expect_http sql https://sql.usegalaxy.eu/login/ 200
expect_http csp https://csp.usegalaxy.eu/ 200
expect_http git https://gitlab.denbi.uni-freiburg.de/users/sign_in 200
expect_http ftp_docs https://ftp.usegalaxy.eu/ 200

expect_http influx http://influxdb.denbi.uni-freiburg.de:8086/ping 204
expect_http sentry https://sentry.denbi.uni-freiburg.de/auth/login/sentry/ 200

expect_ftps ftp_ssl ftp://ftp.usegalaxy.eu
expect_gx_ftp_age ftp_age https://usegalaxy.eu
