#!/bin/bash
condor_q -global -total | grep "all\|Schedd"  | while read hostline; read numbersline; do                                                                                        
    host=$(echo $hostline | awk -F": " '{gsub(/ /, "", $2); print$2}');
    echo $numbersline | sed 's/.* jobs;\s*//g;s/, /\n/g' | while read line; do
        type=$(echo $line | sed 's/^[0-9]* //g');
        count=$(echo $line | sed 's/ .*//g');
        echo cluster.queue,engine=condor,schedd="$host",state=$type count=$count
    done;
done;
