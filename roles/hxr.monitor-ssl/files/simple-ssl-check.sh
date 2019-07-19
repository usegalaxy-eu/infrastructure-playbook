#!/bin/bash

for HOST in "$@"; do
	cert="$(echo | openssl s_client -servername "$HOST" -connect "$HOST" 2>/dev/null)"
	certExit=$?

	if [[ $certExit -eq 0 ]]; then
		exprDate=$(echo "$cert" | openssl x509 -noout -dates | grep notAfter | sed 's/notAfter=//g' | awk '{print $1,$2,$4}');
		unixExprDate=$(date -d "$exprDate" '+%s')
		secondsToExpr=$(echo "$unixExprDate - $(date '+%s')" | bc)
		echo "ssl.expiry,server=$HOST value=$secondsToExpr"
	else
		echo "ssl.expiry,server=$HOST value=-1"
	fi
done
