# infrastructure-playbook
Ansible playbook for managing Galaxy infrastructure. For the playbook managing Galaxy itself, see https://github.com/galaxyproject/usegalaxy-playbook/

## To run

```shell
% ansible-playbook -i galaxyenv/inventory [--limit=inventoryhost] --vault=/path/to/pass/wrapper playbook.yml
```

My `/path/to/pass/wrapper` is just a shell script that calls `pass path/to/vault/pass`.
