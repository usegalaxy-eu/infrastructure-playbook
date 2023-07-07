#!/bin/bash
# mem_total=$(condor_status -autoformat TotalMemory | paste -s -d'+' | bc)
# mem_alloc=$(condor_status -autoformat Memory      | paste -s -d'+' | bc)
# mem_perc=$(echo "$mem_alloc / $mem_total" | bc -l)
# cpu_total=$(condor_status -autoformat DetectedCpus | paste -s -d'+' | bc)
# cpu_alloc=$(condor_status -autoformat Cpus         | paste -s -d'+' | bc)
# cpu_perc=$(echo "$cpu_alloc / $cpu_total" | bc -l)
# echo "cluster.alloc,cluster=condor cores=0$cpu_perc,memory=0$mem_perc"

# As of 04.07.2023, the following is used to collect data from the cluster
# Details:
# SlotType: Dynamic or partitionable slots. Each host is partitioned to 1 slot and that slot is further dynamically partitioned to several slots
# Name: Name of the slot
# State: Claimed or Unclaimed slot
# Activity: Idle or Busy
# DetectedCpus: Total CPU cores available at machine level
# Cpus: Total CPU cores available at slot level
# TotalMemory: Total memory available at machine level
# Memory: Total memory available at slot level
# LoadAvg: Load avergate at slot level
# TotalLoadAvg: Total load average at the machine level
# GalaxyGroup: Group name of the machine

# Command:
condor_status -af:l Name SlotType State Activity GalaxyGroup DetectedCpus Cpus TotalMemory Memory LoadAvg TotalLoadAvg -constraint 'SlotType == "Dynamic" || SlotType == "Partitionable"' | awk -F '[= ]+' '{printf("htcondor_cluster_usage,classad=\"slot\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=%s,%s=%s,%s=%s,%s=%s,%s=%s,%s=%s %s=\"%s\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=%s,%s=%s,%s=%s,%s=%s,%s=%s,%s=%s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)}'
