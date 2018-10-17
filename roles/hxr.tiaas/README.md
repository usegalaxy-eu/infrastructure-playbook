# TIaaS Group Join Service

Install and configure [this mess](https://github.com/usegalaxy-eu/tiaas-group-join).

TODO:
- add systemd unit when can migrate to new host

Requirements
------------

RHEL / Centos7 / Centos6

Role Variables
--------------

```
tiaas_galaxy_db_url: postgres
tiaas_redirect_url: "https://usegalaxy.eu"
tiaas_galaxy_idsecret: "DEFAULT IS INSECURE!"
tiaas_galaxy_url: "https://usegalaxy.eu"
tiaas_galaxy_key: "deadbeefcafe"
tiaas_trainings:
  - test
tiaas_dir: /opt/tiaas-group-join
tiaas_user: root
tiaas_group: root
tiaas_version: master
```

Dependencies
------------

None.

Example Playbook
----------------

TODO

License
-------

GPL3

Author Information
------------------

[Helena Rasche](https://github.com/erasche)
