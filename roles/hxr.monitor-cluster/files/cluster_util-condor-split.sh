#!/bin/bash
subclusters=$(condor_status -autoformat Machine | egrep -v '[a-z][0-9]{4}.novalocal' | sed -r 's/-[0-9]{4}.novalocal//g;s/vgcnbwc-//g;' | sort | uniq)
for cluster in $subclusters; do
	mem_total=$(condor_status  -autoformat TotalMemory Machine Activity | grep -- "-$cluster-" | grep Idle| awk '{print $1}' | paste -s -d'+' | bc)
	mem_remain=$(condor_status -autoformat Memory      Machine Activity | grep -- "-$cluster-" | grep Idle| awk '{print $1}' | paste -s -d'+' | bc)
	mem_perc=$(echo "($mem_total - $mem_remain) / $mem_total" | bc -l)
	cpu_total=$(condor_status  -autoformat DetectedCpus Machine Activity | grep -- "-$cluster-" | grep Idle | awk '{print $1}' | paste -s -d'+' | bc)
	cpu_remain=$(condor_status -autoformat Cpus         Machine Activity | grep -- "-$cluster-" | grep Idle | awk '{print $1}' | paste -s -d'+' | bc)
	cpu_perc=$(echo "($cpu_total - $cpu_remain) / $cpu_total" | bc -l)
	echo "cluster.alloc,cluster=condor-sep,group=$cluster cores=0$cpu_perc,memory=0$mem_perc"
done
