#! /bin/bash
GALAXY_API_KEY=$(cat /etc/gx-api-creds.json | jq .api_key -r)
GALAXY_NAME=$(cat /etc/gx-api-creds.json | jq .galaxy_test_name -r)

expect_http() {
	service=$1
	url=$2
	expected_status=$3

	t_start=$(date +%s.%N)
	curl_output=$(timeout 10 curl 2>/dev/null --silent --connect-timeout 10 $url -I)
	if [[ $? -eq 0 ]]; then
		response_code=$(echo $curl_output | head -n1 | awk '{print $2}');
		if [[ $response_code -eq $expected_status ]]; then
			status=0
		else
			status=1
		fi
	else
		response_code=999
		status=1
	fi

	t_end=$(date +%s.%N)
	t_delta=$(echo "1000000 * ($t_end - $t_start)" | bc -l)
	t_delta=$(echo $t_delta | sed 's/\..*//')
	echo "$GALAXY_NAME.pages,page=$service code=$response_code,request_time=0$t_delta,status=$status"
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

	echo "$GALAXY_NAME.services,service=$service request_time=0$t_delta,status=$exit_code"

}

expect_gx_ftp_age() {
	service=$1
	url=$2
	t_start=$(date +%s.%N)
	# Fetch the timestamp from the remote_files api
	curl_output=$(timeout 6 curl --connect-timeout 6 --silent $url/api/remote_files?key=$GALAXY_API_KEY)
	if [[ $? -eq 0 ]]; then
		timestamp=$(echo $curl_output | jq '.[] | select(.path = "nagios") | .ctime' -r)
		# Parse the date
		created_at=$(date --date="$timestamp" "+%s")
		now=$(date "+%s")
		# Calculate its age.
		file_age=$(echo "$now - $created_at" | bc)
	else
		file_age=600
	fi

	t_end=$(date +%s.%N)
	t_delta=$(echo "1000000 * ($t_end - $t_start)" | bc -l)
	t_delta=$(echo $t_delta | sed 's/\..*//')

	# Allow the file to be up to 300 seconds (5 minutes) old
	if [[ $file_age -lt 300 ]]; then
		status=0
	else
		status=1
	fi

	echo "$GALAXY_NAME.services,service=$service request_time=0$t_delta,status=$status"
}
