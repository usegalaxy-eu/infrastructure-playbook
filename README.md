# usegalaxy.eu infrastructure playbook

Ansible playbook for managing UseGalaxy.EU infrastructure. For the playbook
managing Galaxy itself, see https://github.com/galaxyproject/usegalaxy-playbook/

## Running Notes

This probably won't work for your infra. We require everything to run on
CentOS7. We make no effort in this repository that the playbooks can be re-used
on other infrastructure as-is.

A virtualenv located at .venv is *required*:

```
virtualenv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Install the ansible roles that are not tracked in this repository

```
ansible-galaxy install -r requirements.yml
```

And then you can run playbooks. No venv activation is required for this step.

```
make cvmfs CHECK=1
```

## Build Statuses

The playbooks are being automatically and regularly run against the following machines:

Server          | Status
---             | ---
Apollo          | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fapollo)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/apollo/)
Build           | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fbuild)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/build/)
Central-Manager | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fcentral-manager)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/central-manager/)
CVMFS           | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fcvmfs)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/cvmfs/)
Docker          | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fdocker)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/docker/)
Galaxy          | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fgalaxy)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/galaxy/)
Galaxy/Test     | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fgalaxy-test)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/galaxy-test/)
Grafana         | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fstats)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/stats/)
HAProxy         | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Fhaproxy-internal)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/haproxy-internal/)
InfluxDB        | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Finfluxdb)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/influxdb/)
Telescope       | [![Build Status](https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2Fplaybooks%2Ftelescope)](https://build.galaxyproject.eu/job/usegalaxy-eu/job/playbooks/job/telescope/)
