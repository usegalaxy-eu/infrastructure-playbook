#!/bin/bash
condor_q -total | grep "all" | sed 's/.* jobs;\s*//g;s/, /\n/g' | while read line ; do
    type=$(echo $line | sed 's/^[0-9]* //g');
    count=$(echo $line | sed 's/ .*//g');
    echo "cluster.queue,engine=condor,state=$type count=$count"
done;
