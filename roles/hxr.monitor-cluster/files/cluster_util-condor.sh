#!/bin/bash
# Details: This script is used to monitor the entire HTCondor cluster usage independent of GalaxyGroup's

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

# Total number of GPU slots
total_gpu_slots=$(condor_status -af Name -constraint 'CUDADeviceName =!= undefined' | wc -l)

# Claimed GPUs slots
claimed_gpus=$(condor_status -af Name -constraint 'State == "Claimed" && CUDADeviceName =!= undefined' | wc -l)

# Unclaimed GPUs slots
unclaimed_gpus=$(condor_status -af Name -constraint 'State == "Unclaimed" && CUDADeviceName =!= undefined' | wc -l)

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

# Output in influxdb protocol format
echo "htcondor_cluster_usage,classad='machine' total_detected_cpus=$total_detected_cpus,claimed_cpus=$claimed_cpus,unclaimed_cpus=$unclaimed_cpus,total_memory=$total_memory,claimed_memory=$claimed_memory,unclaimed_memory=$unclaimed_memory,total_loadavg=$total_loadavg,claimed_loadavg=$claimed_loadavg,unclaimed_loadavg=$unclaimed_loadavg,total_slots=$total_slots,claimed_busy_slots=$claimed_busy_slots,unclaimed_idle_slots=$unclaimed_idle_slots,total_gpu_slots=$total_gpu_slots,claimed_gpus=$claimed_gpus,unclaimed_gpus=$unclaimed_gpus"

