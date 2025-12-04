LAUNCH_VM := 0
DEBUG :=
ifdef CHECK
  CHECK_C := --check --diff
else
  CHECK_C :=
endif
ifdef DIFF
  DIFF_C := --diff
else
  DIFF_C :=
endif

OTHER :=


help:
	@echo "Run 'make [grafana|jenkins|haproxy|...].yml' to re-run ansible for that machine."
	@echo ""
	@echo "Make Variables: (make ... VAR=VALUE)"
	@echo "  DIFF=1         show changes made"
	@echo "  CHECK=1      run in --check mode (implies DIFF=1)"

deps: requirements.yaml
	bash bin/clean-deps.sh
	ansible-galaxy install -r requirements.yaml

known_hosts:
	grep --quiet '^apps.galaxyproject.eu' ~/.ssh/known_hosts || echo "[apps.galaxyproject.eu]:8080 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPqyqSMGttoZKjzVQh9deKhdX0CxWGjn0v2hHIzM1Fbt" >> ~/.ssh/known_hosts
	grep --quiet '^osiris.denbi.de' ~/.ssh/known_hosts || echo "osiris.denbi.de ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINZMRlC7VfGh2XBExqH74UZZg6ZUc1d/Ok2adr5ostBV" >> ~/.ssh/known_hosts
	grep --quiet '^worker-0.gold.build.galaxyproject.eu' ~/.ssh/known_hosts || echo "worker-0.gold.build.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAjC0YY4V6gDjvIyFb1qyszQn+Jr2GtLImSJO5BVoeHq" >> ~/.ssh/known_hosts
	grep --quiet '^worker-0.bronze.build.galaxyproject.eu' ~/.ssh/known_hosts || echo "worker-0.bronze.build.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKE2VMZbiOf4NHTVyNj9FyCu2P71YF/RHHO97lrsPC46" >> ~/.ssh/known_hosts
	grep --quiet '^upload.galaxyproject.eu' ~/.ssh/known_hosts || echo "upload.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIO9oCi9GY9fyZvwvqh0t0LnpL4DEVo/SXqUhZcc8RbNS" >> ~/.ssh/known_hosts
	grep --quiet '^sn10.galaxyproject.eu' ~/.ssh/known_hosts || echo "sn10.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC49py5wws/7FhAfRDRS8byDMbSaqxNj3ddigSoXJM/y" >> ~/.ssh/known_hosts
	grep --quiet '^sn12.galaxyproject.eu' ~/.ssh/known_hosts || echo "sn12.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMoOla00b8+03VlVu9TOHJbij41jFILenJ2zWHsZE8fh" >> ~/.ssh/known_hosts
	grep --quiet '^dnbd3-primary.galaxyproject.eu' ~/.ssh/known_hosts || echo "dnbd3-primary.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDYEBgKM/tY4GApGBuD0sS6A33kfGPqmZTDwfR3QdlK9" >> ~/.ssh/known_hosts
	grep --quiet '^@cert-authority' ~/.ssh/known_hosts || echo "@cert-authority *.galaxyproject.eu,*.usegalaxy.eu,*.bi.privat,192.52.33.*,192.52.32.*,10.4.68.*,10.5.68.* ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDLQD6fG38uwFj91GSe6YnRnBuTjXWZN6Pck1JRCTWtufwKV0SZNczD+qUdnFfZrCx/wBVK8R6zL2VWS9hcFK1LuE8HK86f8qG/gcB6yFt/0I/PWoSjcbUMPQTzFIy8yxvdIoPTlj/P6+uNgweTvMFI4+UOuCI71IhB/liTHn1/2dXQM94SFd4VQeg+3Tc6gDxEqRSS6dLIq0uvR8//luIpoW38yh2ozwHmjMKTvHnbduGqHlES4qz9cU9iZkWoPzSp+qoxCOijHvwzL5vD0/k4hZ/iJyTzDHQLDra3Kaa8ykWdERCxjpMp1y9dVQ23lVxp+UUAt3RHOCU1/KuNM9Pr" >> ~/.ssh/known_hosts
	grep --quiet '^sn04.bi.uni-freiburg.de' ~/.ssh/known_hosts || echo "sn04.bi.uni-freiburg.de,132.230.68.5 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBNC78hpzimTnM3yI8EiW1UPOwUOflHyWHJhTsxv3RD0EMtOajnQQLwjuO7KZUgPpT0JabBxsrtTL+prny8IpB3Y=" >> ~/.ssh/known_hosts

pull:
	git fetch origin
	git reset --hard origin/master

test.eu:
	ansible-playbook galaxy-test.yml $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER) --extra-vars "__galaxy_dir_perms='0755'"

main.eu: deps
	ansible-playbook sn09.yml      $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER) --extra-vars "__galaxy_dir_perms='0755'"

%.yml: deps
	ansible-playbook $@ $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER)

.PHONY: test.eu main.eu known_hosts deps pull help
