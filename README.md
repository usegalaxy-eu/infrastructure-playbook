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
