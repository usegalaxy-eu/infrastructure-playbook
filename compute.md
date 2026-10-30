<a href='https://build.galaxyproject.eu/job/usegalaxy-eu/job/VGCN-Infrastructure-Playbook/'><img src='https://build.galaxyproject.eu/buildStatus/icon?job=usegalaxy-eu%2FVGCN-Infrastructure-Playbook'></a>
# VGCN Infrastructure Playbook
## What this does
- Install and configure HTCondor, based on group based variables
- Add HTCondor Token for EU
- Install AutoFS and configure mountpoints
- Add a Telegraf `output.conf` with Galaxy Europe's Telegraf credentials
## Requirements
- Vault password
- Mountpoints variables from https://github.com/usegalaxy-eu/mounts
