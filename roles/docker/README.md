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
