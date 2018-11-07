# ansible-role-yum

[![Build Status](https://travis-ci.org/linuxhq/ansible-role-yum.svg?branch=master)](https://travis-ci.org/linuxhq/ansible-role-yum)

RHEL/CentOS - Package upgrades, permissions setting, plugin configuration and scheduled updates

## Requirements

None

## Role Variables

Available variables are listed below, along with default values:

    yum_cron: true
    yum_cron_conf:
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
    yum_cron_hourly_conf:
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
    yum_module_opts:
      allow_downgrade: false
      conf_file: ''
      disable_gpg_check: false
      disablerepo: []
      enablerepo: []
      exclude: ''
      installroot: /
      security: false
      skip_broken: false
      update_cache: false
      validate_certs: true
    yum_packages_install: []
    yum_packages_remove: []
    yum_packages_update: true
    yum_permissions: []
    yum_plugin_packages:
      - yum-plugin-fastestmirror
      - yum-plugin-post-transaction-actions
    yum_plugin_fastestmirror:
      always_print_best_host: true
      enabled: 1
      hostfilepath: timedhosts.txt
      maxhostfileage: 10
      maxthreads: 15
      socket_timeout: 3
      verbose: 0
    yum_plugin_post_transaction_actions:
      actiondir: /etc/yum/post-actions/
      actions: []
      enabled: 1
    yum_protected:
      systemd:
        - systemd

## Dependencies

None

## Example Playbook

    - hosts: servers
      roles:
        - role: linuxhq.yum
          yum_module_opts:
            enablerepo:
              - epel
          yum_packages_install:
            - bind-utils
            - wget
          yum_permissions:
            - path: /bin/su
              owner: root
              group: root
              mode: 700
          yum_plugin_post_transaction_actions:
            actiondir: /etc/yum/post-actions/
            actions:
              - action_key: kernel-ml
                transaction_state: install
                command: /usr/sbin/shutdown -r
            enabled: 1

## License

GPLv3

## Author Information

This role was created by [Taylor Kimball](http://www.linuxhq.org).
