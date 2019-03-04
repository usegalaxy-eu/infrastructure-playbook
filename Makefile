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


help:
	@echo "Run 'make [grafana|jenkins|haproxy|...].yml' to re-run ansible for that machine."
	@echo ""
	@echo "Make Variables: (make ... VAR=VALUE)"
	@echo "  DIFF=1         show changes made"
	@echo "  CHECK=1      run in --check mode (implies DIFF=1)"

deps: requirements.yaml
	.venv/bin/ansible-galaxy install -r requirements.yaml
	@# make deps 2>&1 | grep force | awk '{print $3}'

pull:
	git fetch origin
	git reset --hard origin/master

%.yml: deps
	.venv/bin/ansible-playbook $@ $(CHECK_C) $(DIFF_C) $(DEBUG)
