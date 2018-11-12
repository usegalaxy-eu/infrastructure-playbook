#!/bin/bash
mem_alloc_sge=$(qstat -u galaxy -ne -s r -r -xml | grep h_vmem | sed 's/<\/.*//' | sed 's/^.*>//;s/G/ * 1024/g;s/M/ * 1/g' | bc | paste -s -d'+' | bc)
mem_total_sge=$(qhost | grep -v -- '-\s*-\s*-' | grep -v cnt | grep -v HOSTNAME | awk '{print $8}' | sed 's/G/* 1024/' | paste -s -d+ | bc)
mem_perc_sge=$(echo "$mem_alloc_sge / $mem_total_sge" | bc -l)
cpu_alloc_sge=$(qstat -u galaxy -ne -s r | grep '^[0-9][0-9]*' | awk '{ print $9}' | paste -s -d'+' | bc)
cpu_total_sge=$(qhost | grep -v -- '-\s*-\s*-' | grep -v cnt | grep -v HOSTNAME | awk '{print $3}' | paste -s -d+ | bc)
cpu_perc_sge=$(echo "$cpu_alloc_sge / $cpu_total_sge" | bc -l)
echo "cluster.alloc,cluster=sge,group=all cores=0$cpu_perc_sge,memory=0$mem_perc_sge"
