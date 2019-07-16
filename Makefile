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

pull:
	git fetch origin
	git reset --hard origin/master

eu.test:
	ansible-playbook galaxy-test.yml $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER) --extra-vars "__galaxy_dir_perms='0755'"

eu.main:
	ansible-playbook galaxy.yml      $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER) --extra-vars "__galaxy_dir_perms='0755'"

%.yml: deps
	.venv/bin/ansible-playbook $@ $(CHECK_C) $(DIFF_C) $(DEBUG) $(OTHER)

.PHONY: eu.test eu.main
