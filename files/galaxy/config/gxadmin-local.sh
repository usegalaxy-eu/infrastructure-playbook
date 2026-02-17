local_cluster-stop-jobs() { ## <hostname>:
        assert_count $# 1 "Must supply hostname"

        ssh $1 sudo bash -c 'for pid in $(pgrep condor_starter); do pstree -p $pid | egrep -o "[0-9]+" | xargs -I{} -n 1 kill -STOP {}; done'
}

local_cluster-resume-jobs() { ## <hostname>:
        assert_count $# 1 "Must supply hostname"

        ssh $1 sudo bash -c 'for pid in $(pgrep condor_starter); do pstree -p $pid | egrep -o "[0-9]+" | xargs -I{} -n 1 kill -CONT {}; done'
}

local_fail-job() { ## fails galaxy job and removes connected HTCondor job
        handle_help "$@" <<-EOF
                This function fails a Galaxy job and removes the relative condor job.
                Provide a Galaxy job id as argument
        EOF

        [ -z $1 ] && echo "Must supply a Galaxy job ID" && exit
        [ -z "condor_queue" ] && echo "ID not found in the HTCondor queue" && exit
        condor_queue=$(condor_q -autoformat Cmd Clusterid | tr " " ";" | grep -v pbs.sh | grep -v uploads.sh|grep $1)
        condor_id=$(echo $condor_queue |cut -f2 -d';')
        gxadmin mutate fail-job $1 --commit
        condor_rm $condor_id
        echo "Failed Galaxy job, id $1, and removed connected HTCondor job, id $condor_id"

}

local_restart-job() { ## restarts galaxy job and removes connected HTCondor job
        handle_help "$@" <<-EOF
                This function restarts a Galaxy job and removes the relative condor job.
                Provide a Galaxy job id as argument
        EOF

        [ -z $1 ] && echo "Must supply a Galaxy job ID" && exit
        condor_queue=$(condor_q -autoformat Cmd Clusterid | tr " " "_" | grep -v job_working_dir.sh|grep $1)
        [ -z "$condor_queue" ] && echo "ID not found in the HTCondor queue" && exit
        condor_id=$(echo $condor_queue |cut -f6 -d_)
        gxadmin mutate restart-jobs --commit $1
        condor_rm $condor_id
        echo "Restarted Galaxy job, id: $1, and removed connected HTCondor job, id: $condor_id"

}

local_monthly_compute_stats() { ## description
        handle_help "$@" <<-EOF
                This function
        EOF

        monthly_cpu_years=$(gxadmin csvquery monthly-cpu-years)
        monthly_jobs=$(gxadmin csvquery monthly-jobs)
        echo "Month,CPU_hours,Monthly_jobs"
        for i in $monthly_cpu_years
        do
                month=$(echo $i |cut -f1 -d,)
                cpu_years=$(echo $i | cut -f2 -d,)
                for j in $monthly_jobs
                do
                        jobs_=$(echo $j | cut -f2 -d,)
                        jobs_month=$(echo $j | cut -f1 -d,)
                        if [ "$month" == "$jobs_month" ]; then
                                cpu_hours=$(echo "$cpu_years * 24 * 365" | bc -l)
                                echo $month, $cpu_hours, $jobs_
                        fi
                done
        done
}
