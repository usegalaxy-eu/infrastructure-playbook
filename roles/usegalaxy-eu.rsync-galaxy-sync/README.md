Role Name
=========

Adds a rsync script that performs a full sync of a Galaxy codebase to an NFS share and the head nodes

Role Variables
--------------

`execute_galaxy_sync`: Whether to execute the sync script or not. Defaults to `false`
`galaxy_rsync_user_private_key_file`: The private key of the user that will be used to rsync the codebase. If this key does not exist then it will be added from the vault file.
`headnodes`: A list of headnodes to rsync the codebase to. Defaults to `sn07.galaxyproject.eu` (this is currently (24/03/2023) in testing phase so the default is `sn07`)
`headnodes_sync_location`: The location on the headnodes to rsync the codebase to. Defaults to the variable `galaxy_root` (which is defined in the group_vars files)

Dependencies
------------

- `prsync` command (if not installed, it will be installed. The command is available in the `pssh` package)

Example Playbook
----------------

    - hosts: maintenance
      roles:
         - role: usegalaxy-eu.rsync-galaxy-sync
           vars:
              execute_galaxy_sync: false
              galaxy_rsync_user_private_key: "/opt/galaxy/.ssh/galaxy_rsync_key"
              headnodes: "sn07.galaxyproject.eu"
              headnodes_sync_location: "/opt/galaxy"
              galaxy_nfs_location: "/data/galaxy-sync"
