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
	grep --quiet '^@cert-authority' ~/.ssh/known_hosts || echo "@cert-authority *.galaxyproject.eu,*.usegalaxy.eu,192.52.33.*,192.52.32.*,10.5.68.* ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQDLQD6fG38uwFj91GSe6YnRnBuTjXWZN6Pck1JRCTWtufwKV0SZNczD+qUdnFfZrCx/wBVK8R6zL2VWS9hcFK1LuE8HK86f8qG/gcB6yFt/0I/PWoSjcbUMPQTzFIy8yxvdIoPTlj/P6+uNgweTvMFI4+UOuCI71IhB/liTHn1/2dXQM94SFd4VQeg+3Tc6gDxEqRSS6dLIq0uvR8//luIpoW38yh2ozwHmjMKTvHnbduGqHlES4qz9cU9iZkWoPzSp+qoxCOijHvwzL5vD0/k4hZ/iJyTzDHQLDra3Kaa8ykWdERCxjpMp1y9dVQ23lVxp+UUAt3RHOCU1/KuNM9Pr" >> ~/.ssh/known_hosts
	grep --quiet '^sn04.bi.uni-freiburg.de' ~/.ssh/known_hosts || echo "sn04.bi.uni-freiburg.de,132.230.68.5 ecdsa-sha2-nistp256 AAAAE2VjZHNhLXNoYTItbmlzdHAyNTYAAAAIbmlzdHAyNTYAAABBBNC78hpzimTnM3yI8EiW1UPOwUOflHyWHJhTsxv3RD0EMtOajnQQLwjuO7KZUgPpT0JabBxsrtTL+prny8IpB3Y=" >> ~/.ssh/known_hosts

pull:
	git fetch origin
	git reset --hard origin/master

test.eu:
	ansible-playbook galaxy-test.yml $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER) --extra-vars "__galaxy_dir_perms='0755'"

main.eu:
	ansible-playbook galaxy.yml      $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER) --extra-vars "__galaxy_dir_perms='0755'"

%.yml: deps
	.venv/bin/ansible-playbook $@ $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER)

.PHONY: test.eu main.eu known_hosts deps pull help
