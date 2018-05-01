#!/bin/bash
properties=used,available,referenced,compressratio,usedbysnapshots,usedbydataset,usedbychildren,usedbyrefreservation,written,logicalused,logicalreferenced

for pool in $(zfs list -H | cut -f1); do
	output=$(zfs get $properties -Hp tank/cvmfs | sed 's/compressratio\(.*\)x/compressratio\1/' | awk '{print $2"="$3}' | paste -d, -s)
	echo "zfs.extra,pool=$pool $output"
done
