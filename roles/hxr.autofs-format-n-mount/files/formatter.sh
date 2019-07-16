#!/bin/bash
grep --quiet vdb /etc/fstab > /dev/null
ec=$?

if (( ec > 0 )); then
	mkfs -t xfs /dev/vdb
	echo "/dev/vdb  /vdb xfs defaults,nofail 0 2" >> /etc/fstab
	mkdir -p /vdb
	mount /vdb
fi
