#!/bin/bash
for cluster in $(condor_status -autoformat GalaxyGroup | sort | grep -v undefined | uniq); do
	mem_total=$(condor_status  -autoformat TotalMemory  -constraint 'GalaxyGroup == "'$cluster'" && Activity == "Idle"' | paste -s -d'+' | bc)
	mem_remain=$(condor_status -autoformat Memory       -constraint 'GalaxyGroup == "'$cluster'" && Activity == "Idle"' | paste -s -d'+' | bc)
	cpu_total=$(condor_status  -autoformat DetectedCpus -constraint 'GalaxyGroup == "'$cluster'" && Activity == "Idle"' | paste -s -d'+' | bc)
	cpu_remain=$(condor_status -autoformat Cpus         -constraint 'GalaxyGroup == "'$cluster'" && Activity == "Idle"' | paste -s -d'+' | bc)
	mem_perc=$(echo "($mem_total - $mem_remain) / $mem_total" | bc -l)
	cpu_perc=$(echo "($cpu_total - $cpu_remain) / $cpu_total" | bc -l)
	echo "cluster.alloc,cluster=condor-sep,group=$cluster cores=0$cpu_perc,memory=0$mem_perc"
done
