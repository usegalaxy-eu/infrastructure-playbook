Groups
======

- `dockerclients` to install docker with the service set to disabled/stopped
- `dockerservers` to install docker with the service set to enabled/started
- `dockersslservers` to additionally install server SSL certificate and key
  (see SSL below)

Docker "clients" get Docker installed but the service is set to disabled/stopped.

SSL
===

To enable SSL communication between a docker client and a remote docker daemon,
add docker daemon hosts to the `dockersslservers` group. The first member of
that group will become the "SSL master" and the CA, server keys, and client key
will be managed from that host.

Be sure to set the `docker_ssl_ca_dn` hash, e.g.:

```yaml
docker_ssl_ca_dn:
  country: US
  state: Pennsylvania
  locality: University Park
  organization: The Pennsylvania State University
  organizational_unit: The Galaxy Project
  common_name: Galaxy Docker CA Root
```

And set the CA key passphrase in `docker_ssl_ca_passphrase`.

Create a list of users who should receive the client key/cert in ~/.docker:

```yaml
docker_ssl_client_users:
  - mal
  - zoe
  - wash
```
