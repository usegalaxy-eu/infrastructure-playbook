#!/bin/bash

# This script is used to monitor the condor jobs status in the cluster including the compute resources, job submit time to the queue, job start time, job description, etc.
condor_q -global -autoformat ClusterId JobStatus Cmd RemoteHost RequestCpus RequestMemory QDate JobStartDate JobDescription | awk '{
  if ($8 != "undefined") $8 = strftime("%Y-%m-%d %H:%M:%S", $8);
  status["0"]="Unexpanded"; status["1"]="Idle"; status["2"]="Running"; status["3"]="Removed"; status["4"]="Completed"; status["5"]="Held"; status["6"]="Submission_err";

  jobdesc = $9;

  for (i = 10; i <= NF; i++) {
    jobdesc = jobdesc "_" $i;
  }

  printf "condor_queued_jobs_status,clusterid=\"%s\" jobstatus=\"%s\",cmd=\"%s\",remotehost=\"%s\",requestcpus=%s,requestmemory=%s,qdate=\"%s\",jobstartdate=\"%s\",jobdescription=\"%s\"\n", $1, status[$2], $3, $4, $5, $6, strftime("%Y-%m-%d %H:%M:%S", $7), $8, jobdesc
}'
