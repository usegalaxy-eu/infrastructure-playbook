# usegalaxy.eu infrastructure playbook

Ansible playbook for managing UseGalaxy.EU infrastructure. For the playbook
managing Galaxy itself, see https://github.com/galaxyproject/usegalaxy-playbook/

## To run

```shell
% make <service>
```

## Adding New Services

Please see testing_vm.yml and testing.yml for examples of apache hosts with letsencrypt certificates.

## Letsencrypt Module

This will **only** function on hosts without a webserver, that do not have existing LE certs (so it should go before apache/nginx setup.)
