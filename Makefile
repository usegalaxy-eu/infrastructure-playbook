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
PLAYBOOKS := $(wildcard *.yml)


help:
	@echo "Run 'make [grafana|jenkins|haproxy|...].yml' to re-run ansible for that machine."
	@echo "Run 'make lint' to yamllint the repository."
	@echo "Run 'make syntax' to syntax-check all top-level playbooks."
	@echo "Run 'make validate' to run deps, lint, and syntax in order."
	@echo ""
	@echo "Make Variables: (make ... VAR=VALUE)"
	@echo "  DIFF=1         show changes made"
	@echo "  CHECK=1      run in --check mode (implies DIFF=1)"

deps: requirements.yaml
	bash bin/clean-deps.sh
	ansible-galaxy install -r requirements.yaml

known_hosts:
	grep --quiet '^influxdb.bi.privat' ~/.ssh/known_hosts || echo "influxdb.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJLhLsIO61hj8Kk6VQWTq5JU+PRm5/so1k44yZQTwvVO" >> ~/.ssh/known_hosts
	grep --quiet '^celery-1.bi.privat' ~/.ssh/known_hosts || echo "celery-1.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFeiWwfhHxx2OVzHvaOQxWnCwlngRD26DxrCKYKMWQD1" >> ~/.ssh/known_hosts
	grep --quiet '^apps.galaxyproject.eu' ~/.ssh/known_hosts || echo "[apps.galaxyproject.eu]:8080 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIPqyqSMGttoZKjzVQh9deKhdX0CxWGjn0v2hHIzM1Fbt" >> ~/.ssh/known_hosts
	grep --quiet '^osiris.denbi.de' ~/.ssh/known_hosts || echo "osiris.denbi.de ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAINZMRlC7VfGh2XBExqH74UZZg6ZUc1d/Ok2adr5ostBV" >> ~/.ssh/known_hosts
	grep --quiet '^plausible.bi.privat' ~/.ssh/known_hosts || echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJLhLsIO61hj8Kk6VQWTq5JU+PRm5/so1k44yZQTwvVO" >> ~/.ssh/known_hosts
	grep --quiet '^worker-0.gold.build.galaxyproject.eu' ~/.ssh/known_hosts || echo "worker-0.gold.build.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAjC0YY4V6gDjvIyFb1qyszQn+Jr2GtLImSJO5BVoeHq" >> ~/.ssh/known_hosts
	grep --quiet '^worker-0.bronze.build.galaxyproject.eu' ~/.ssh/known_hosts || echo "worker-0.bronze.build.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKE2VMZbiOf4NHTVyNj9FyCu2P71YF/RHHO97lrsPC46" >> ~/.ssh/known_hosts
	grep --quiet '^beacon.bi.privat' ~/.ssh/known_hosts || echo "beacon.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJLhLsIO61hj8Kk6VQWTq5JU+PRm5/so1k44yZQTwvVO" >> ~/.ssh/known_hosts
	grep --quiet '^upload.bi.privat' ~/.ssh/known_hosts || echo "upload.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIHMz9KPAC6tZwxoBE0tcqDVA29mPtE3K+so9MYGsNkNU" >> ~/.ssh/known_hosts
	grep --quiet '^sn10.galaxyproject.eu' ~/.ssh/known_hosts || echo "sn10.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIC49py5wws/7FhAfRDRS8byDMbSaqxNj3ddigSoXJM/y" >> ~/.ssh/known_hosts
	grep --quiet '^central-manager.bi.privat' ~/.ssh/known_hosts || echo "central-manager.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMoOla00b8+03VlVu9TOHJbij41jFILenJ2zWHsZE8fh" >> ~/.ssh/known_hosts
	grep --quiet '^sn12.galaxyproject.eu' ~/.ssh/known_hosts || echo "sn12.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIMoOla00b8+03VlVu9TOHJbij41jFILenJ2zWHsZE8fh" >> ~/.ssh/known_hosts
	grep --quiet '^dnbd3-primary.galaxyproject.eu' ~/.ssh/known_hosts || echo "dnbd3-primary.galaxyproject.eu ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDYEBgKM/tY4GApGBuD0sS6A33kfGPqmZTDwfR3QdlK9" >> ~/.ssh/known_hosts
	grep --quiet '^@cert-authority' ~/.ssh/known_hosts || echo "@cert-authority *.galaxyproject.eu,*.usegalaxy.eu,*.bi.privat,192.52.33.*,192.52.32.*,10.4.68.*,10.5.68.* ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDLQD6fG38uwFj91GSe6YnRnBuTjXWZN6Pck1JRCTWtufwKV0SZNczD+qUdnFfZrCx/wBVK8R6zL2VWS9hcFK1LuE8HK86f8qG/gcB6yFt/0I/PWoSjcbUMPQTzFIy8yxvdIoPTlj/P6+uNgweTvMFI4+UOuCI71IhB/liTHn1/2dXQM94SFd4VQeg+3Tc6gDxEqRSS6dLIq0uvR8//luIpoW38yh2ozwHmjMKTvHnbduGqHlES4qz9cU9iZkWoPzSp+qoxCOijHvwzL5vD0/k4hZ/iJyTzDHQLDra3Kaa8ykWdERCxjpMp1y9dVQ23lVxp+UUAt3RHOCU1/KuNM9Pr" >> ~/.ssh/known_hosts
	grep --quiet '^sn04.bi.uni-freiburg.de' ~/.ssh/known_hosts || echo "sn04.bi.uni-freiburg.de,132.230.68.5 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBNC78hpzimTnM3yI8EiW1UPOwUOflHyWHJhTsxv3RD0EMtOajnQQLwjuO7KZUgPpT0JabBxsrtTL+prny8IpB3Y=" >> ~/.ssh/known_hosts
	grep --quiet '^mq.bi.privat' ~/.ssh/known_hosts || echo "mq.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJLhLsIO61hj8Kk6VQWTq5JU+PRm5/so1k44yZQTwvVO" >> ~/.ssh/known_hosts
	grep --quiet '^maintenance.bi.privat' ~/.ssh/known_hosts || echo "maintenance.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJLhLsIO61hj8Kk6VQWTq5JU+PRm5/so1k44yZQTwvVO" >> ~/.ssh/known_hosts
	grep --quiet '^tpv-broker.bi.privat' ~/.ssh/known_hosts || echo "tpv-broker.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJLhLsIO61hj8Kk6VQWTq5JU+PRm5/so1k44yZQTwvVO" >> ~/.ssh/known_hosts
	grep --quiet '^github.com' ~/.ssh/known_hosts || echo "github.com ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCj7ndNxQowgcQnjshcLrqPEiiphnt+VTTvDP6mHBL9j1aNUkY4Ue1gvwnGLVlOhGeYrnZaMgRK6+PKCUXaDbC7qtbW8gIkhL7aGCsOr/C56SJMy/BCZfxd1nWzAOxSDPgVsmerOBYfNqltV9/hWCqBywINIR+5dIg6JTJ72pcEpEjcYgXkE2YEFXV1JHnsKgbLWNlhScqb2UmyRkQyytRLtL+38TGxkxCflmO+5Z8CSSNY7GidjMIZ7Q4zMjA2n1nGrlTDkzwDCsw+wqFPGQA179cnfGWOWRVruj16z6XyvxvjJwbz0wQZ75XK5tKSb7FNyeIEs4TT4jk+S4dhPeAUC5y+bDYirYgM4GC7uEnztnZyaVWQ7B381AK4Qdrwt51ZqExKbQpTUNn+EjqoTwvqNj4kqx5QUCI0ThS/YkOxJCXmPUWZbhjpCg56i+2aB6CmK2JGhn57K5mj0MNdBXA4/WnwH6XoPWJzK5Nyu2zB3nAZp+S5hpQs+p1vN1/wsjk=" >> ~/.ssh/known_hosts
	grep --quiet '^apollo.bi.privat' ~/.ssh/known_hosts || echo "apollo.bi.privat ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJLhLsIO61hj8Kk6VQWTq5JU+PRm5/so1k44yZQTwvVO" >> ~/.ssh/known_hosts

pull:
	git fetch origin
	git reset --hard origin/master

main.eu: deps
	ansible-playbook sn09.yml      $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER) --extra-vars "__galaxy_dir_perms='0755'"

lint:
	yamllint .
	ansible-lint

syntax:
	set -e; \
	for playbook in $(PLAYBOOKS); do \
		echo "Syntax-checking $$playbook"; \
		ansible-playbook --syntax-check $$playbook; \
	done

validate: deps lint syntax

%.yml: deps
	ansible-playbook $@ $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER)

.PHONY: main.eu lint syntax validate known_hosts deps pull help
