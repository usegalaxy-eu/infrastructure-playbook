#!/bin/bash
for file in $(find /var/spool/mail/ -type f); do
	luser=$(basename $file)
	count=$(grep -c '^From: ' $file)
	echo "mail,luser=$luser count=$count";
done
