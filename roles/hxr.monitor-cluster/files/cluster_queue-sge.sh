#!/bin/bash
qstat | awk '(NR>2){print $5}' | uniq -c | awk '{print "cluster.queue,engine=sge,state="$2" count="$1}'
