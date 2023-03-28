Role Name
=========

usegalaxy-eu.vgcn-monitoring

Requirements
------------

Python requirements:
  - GitPython
  - PyYAML
  - python-openstackclient

_Note: These are installed in the `galaxy` venv; look into headnodes (sn06.yml, and sn07.yml) group_vars files_

System requirements:
  - condor_status

Role Variables
--------------

Role variables are defined in `defaults/main.yml`

Description of some variables:

  - `vgcn_infra_repo`: Github repository link for the vgcn-infrastructure repository (default: `https://github.com/usegalaxy-eu/vgcn-infrastructure`)
  - `vgcn_repo_dest_dir`: path to the directory where the vgcn-infrastructure repository will be cloned (default: `/tmp/vgcn-infrastructure-repo`)
  - `custom_vgcn_env`: Defines all OpenStack environment variables and the path to the Python executable (All OpenStack environment variables are defined in the vault file)

Example Playbook
----------------

    - hosts: maintenance
      roles:
         - usegalaxy-eu.vgcn-monitoring
