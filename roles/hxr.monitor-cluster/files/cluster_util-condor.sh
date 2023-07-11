#!/bin/bash
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
# condor_status -af:l Name SlotType State Activity GalaxyGroup DetectedCpus Cpus TotalMemory Memory LoadAvg TotalLoadAvg -constraint 'SlotType == "Dynamic" || SlotType == "Partitionable"' | awk -F '[= ]+' '{printf("htcondor_cluster_usage,classad=\"slot\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=%s,%s=%s,%s=%s,%s=%s,%s=%s,%s=%s %s=\"%s\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=\"%s\",%s=%s,%s=%s,%s=%s,%s=%s,%s=%s,%s=%s\n", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22, $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)}'

# Total number of detected CPUs at the machine level
total_detected_cpus=$(condor_status -af DetectedCpus -constraint 'SlotType == "Partitionable"' | paste -s -d'+' | bc)

# Claimed CPUs
claimed_cpus=$(condor_status -af Cpus -constraint 'State == "Claimed"' | paste -s -d'+' | bc)

# Unclaimed CPUs
unclaimed_cpus=$(condor_status -af Cpus -constraint 'State == "Unclaimed"' | paste -s -d'+' | bc)

# Total memory at the machine level
total_memory=$(condor_status -af TotalMemory -constraint 'SlotType == "Partitionable"' | paste -s -d'+' | bc)

# Claimed memory
claimed_memory=$(condor_status -af Memory -constraint 'State == "Claimed"' | paste -s -d'+' | bc)

# Unclaimed memory
unclaimed_memory=$(condor_status -af Memory -constraint 'State == "Unclaimed"' | paste -s -d'+' | bc)

# Total load average at the machine level
total_loadavg=$(condor_status -af TotalLoadAvg -constraint 'SlotType == "Partitionable"' | paste -s -d'+' | bc)

# Claimed load average
claimed_loadavg=$(condor_status -af LoadAvg -constraint 'State == "Claimed"' | paste -s -d'+' | bc)

# Unclaimed load average
unclaimed_loadavg=$(condor_status -af LoadAvg -constraint 'State == "Unclaimed"' | paste -s -d'+' | bc)

# Total number of slots
total_slots=$(condor_status -af Name -constraint 'SlotType == "Partitionable" || SlotType == "Dynamic" ' | wc -l)

# Total number of Claimed slots with Activity Busy
claimed_busy_slots=$(condor_status -af Name -constraint 'State == "Claimed" && Activity == "Busy"' | wc -l)

# Total number of Unclaimed slots with Activity Idle
unclaimed_idle_slots=$(condor_status -af Name -constraint 'State == "Unclaimed" && Activity == "Idle"' | wc -l)
