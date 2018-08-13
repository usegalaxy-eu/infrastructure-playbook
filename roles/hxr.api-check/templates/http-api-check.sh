#!/usr/bin/env bash
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
	echo "http-api-check,page=$service code=$response_code,request_time=0$t_delta,status=$status"
}

{% for c in http_api_check %}
expect_http {{ c.name }} {{ c.url }} {{ c.code }}
{% endfor %}
