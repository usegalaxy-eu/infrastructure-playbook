#!/bin/bash
squeue | \
	awk '(NR>1){ print $2" "$4" "$5}' | \
	uniq -c | \
	awk '{print "cluster.queue,engine=slurm,state="$4",queue="$2",owner="$3" count="$1}'
