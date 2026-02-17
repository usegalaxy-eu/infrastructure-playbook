# Ansible role: systemd-nspawn

A role that runs a container using systemd-nspawn. Only works on RHEL-based
systems, and can only run RHEL-based containers.

# Requirements

No specific requirements, the role is self-contained.

# Role variables

Default values are available on
[defaults/main.yml](https://github.com/usegalaxy-eu/infrastructure-playbook/blob/main/roles/kysrpex.systemd-nspawn/defaults/main.yml).

```yaml
nspawn_name: container_name
```

Name assigned to the container. It will show up when invoking
`machinectl list`, and can be used with `machinectl` commands, such as
`machinectl shell container_name`.

```yaml
nspawn_distro: "rocky"
nspawn_release: "9"
```

Distribution to base the container's rootfs on. The root file system of the
container is built using [DNF](https://en.wikipedia.org/wiki/DNF_(software))
and one of the configuration files in the
[templates](https://github.com/usegalaxy-eu/infrastructure-playbook/blob/main/roles/kysrpex.systemd-nspawn/templates)
folder. `nspawn_distro` determines the template to use, and `nspawn_release` is
passed to DNF so that it installs the correct distribution release.

```yaml
nspawn_packages:
  - dhcp-client
  - dnf
  - glibc-langpack-en
  - iproute
  - iputils
  - less
  - passwd
  - systemd
  - dbus
  - vim-minimal
```

List of packages to preinstall in the container's rootfs. They will be pulled
from the distribution's repositories using DNF.

```yaml
nspawn_config: |
  # systemd-nspawn container configuration file
  [Exec]
  NotifyReady=yes
```

Configuration file for the container. See the
[systemd.nspawn manpage](https://manpages.debian.org/unstable/systemd-container/systemd.nspawn.5.en.html).

```yaml
nspawn_enable: true
nspawn_start: true
```

Whether to enable (meaning that it will autostart at boot) and/or start the
container after creating it.

# Dependencies

None.

# Example Playbook

```yaml
- name: Run a systemd-nspawn container.
  hosts: host-machines
  vars:
    nspawn_name: container_name
    nspawn_distro: "rocky"
    # only distros that use DNF/YUM and are supported by the role, check the
    # templates directory
    nspawn_release: "9"
    # any release of the supported distros
    nspawn_packages:
      # list of packages to install in the container's rootfs
      - dhcp-client
      - dnf
      - glibc-langpack-en
      - iproute
      - iputils
      - less
      - passwd
      - systemd
      - dbus
      - vim-minimal
    nspawn_config: |
      # systemd-nspawn container configuration file
      [Exec]
      NotifyReady=yes
  pre_tasks:
    # This role does not configure SELinux in a way such that it coexists with
    # systemd-nspawn. If SELinux is enabled on your system, do NOT use this
    # role.
    - name: Disable SELinux.
      become: true
      ansible.posix.selinux:
        state: disabled
  roles:
    - kysrpex.systemd_nspawn
```
