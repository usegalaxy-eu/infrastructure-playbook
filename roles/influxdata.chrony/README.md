Chrony
=========

[![Ansible Galaxy](https://img.shields.io/badge/ansible--galaxy-influxdata.chrony-blue.svg)](https://galaxy.ansible.com/influxdata/chrony/)

Manages the Chrony services on Linux.

Chrony is a service for keeping your servers time in sync, similar to NTPd, see https://chrony.tuxfamily.org/ for more.

_This role will use the AWS Time Sync server by default, see: http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/set-time.html_

Requirements
------------

None, a Linux host only.

Role Variables
--------------

For a list of configuration variables available see the `defaults/main.yml`

Example Usage
----------------

Including an example of how to use your role (for instance, with variables passed in as parameters) is always nice for users too:

    - hosts: all
      roles:
         - { role: influxdata.chrony }

License
-------

MIT

Author Information
------------------

This role is maintained by InfluxData, https://www.influxdata.com, we like time!
