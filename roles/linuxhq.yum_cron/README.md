# ansible-role-yum_cron

[![Build Status](https://travis-ci.org/linuxhq/ansible-role-yum_cron.svg?branch=master)](https://travis-ci.org/linuxhq/ansible-role-yum_cron)
[![Ansible Galaxy](https://img.shields.io/badge/ansible--galaxy-yum_cron-blue.svg?style=flat)](https://galaxy.ansible.com/linuxhq/yum_cron)
[![License](https://img.shields.io/badge/license-GPLv3-brightgreen.svg?style=flat)](COPYING)

RHEL/CentOS - An interface to conveniently call yum from cron

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    yum_cron:
      base:
        debuglevel: -2
        mdpolicy: 'group:main'
      commands:
        apply_updates: false
        download_updates: true
        random_sleep: 360
        update_cmd: default
        update_messages: true
      email:
        email_from: root@localhost
        email_host: localhost
        email_to: root
      emitters:
        emit_via: stdio
        output_width: 80
        system_name: None
      groups:
        group_list: None
        package_types:
          - mandatory
          - default
    yum_cron_hourly:
      base:
        debuglevel: -2
        mdpolicy: 'group:main'
      commands:
        apply_updates: false
        download_updates: false
        random_sleep: 15
        update_cmd: default
        update_messages: false
      email:
        email_from: root
        email_host: localhost
        email_to: root
      emitters:
        emit_via: stdio
        output_width: 80
        system_name: None
      groups:
        group_list: None
        package_types:
          - mandatory
          - default

## Dependencies

None

## Example Playbook

    - hosts: servers
      roles:
        - role: linuxhq.yum_cron

## License

Copyright (C) 2018 Taylor Kimball <tkimball@linuxhq.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
