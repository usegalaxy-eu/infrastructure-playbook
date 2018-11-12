# Monitor Cluster Queues

Install and configure some scripts for monitoring HTCondor/SGE/???.

This role will install the monitoring scripts and **automatically** register them with dj-wasabi.telegraf.

## Requirements

All relevant cluster engines that you wish to monitor should be installed

## Role Variables

variable                    | type    | description
--------------------------- | ---     | ----------
`monitor_condor`            | boolean | Install monitoring scripts for HTCondor
`monitor_condor_split_util` | boolean | Should we send the split monitor
`monitor_sge`               | boolean | Install monitoring scripts for SGE
`monitor_slurm`             | boolean | Install monitoring scripts for SLURM

Dependencies
------------

dj-wasabi.telegraf

Example Playbook
----------------

Configure all hosts as CVMFS clients with configurations for the Galaxy CVMFS repositories:

```yaml
- name: a-single-condor-host
  hosts: all
  vars:
    monitor_condor: true
  roles:
    - usegalaxy-eu.monitor-cluster
```

License
-------

GPLv3

Author Information
------------------

[Helena Rasche](https://github.com/erasche)
