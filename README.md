# usegalaxy.eu infrastructure playbook

Ansible playbook for managing UseGalaxy.EU infrastructure. For the playbook
managing Galaxy itself, see https://github.com/galaxyproject/usegalaxy-playbook/

## To run

```shell
% make <service>
```

Make target   | OS        | Status     | Purpose
---           | --------- | ---        | ---
centos        | -         | Complete   | Tasks to apply to all centos hosts
ubuntu        | -         | Complete   | Tasks to apply to all ubuntu hosts
apollo        | centos    | WIP        | Apollo genome editor server
build01       | centos    | Complete   | RZ Jenkins Build server
cvmfs         | centos    | Complete   | Stratum 1 server
ftp           | centos    | Complete   | FTP Server for galaxy
galaxy        | centos    | WIP        | UseGalaxy.eu stuff
haproxy       | centos    | Complete   | Frontend for UseGalaxy.eu
hpc_grafana   | centos    | Complete   | Duplicate of grafana for hpc stuff
influxdb      | centos    | WIP        | Stats DB for entire infra. TODO: hostname + NFS
sentry        | centos    | Complete   | Sentry + GitHub Auth
gitlab        | ubuntu    | WIP        | ???
grafana       | ubuntu    | Complete   | Statistics dashboard host. TODO: backup data to nfs mount
jenkins       | ubuntu    | Complete   | build.usegalaxy.eu
telescope     | ubuntu    | WIP        | GRT TODO: NFS
gitlab-runner | ubuntu    | Deprecated | Never got this working / never finished
csp-report    | ubuntu    | Deprecated | Content security policy reporting host (deprecated for sentry, hopefully.)

## hxr.certbot Module

This will **only** function on hosts without a webserver, that do not have existing LE certs (so it should go before apache/nginx setup.)

