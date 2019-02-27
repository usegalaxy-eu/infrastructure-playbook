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
	@echo "Run 'make [grafana|jenkins|haproxy|...]' to re-run ansible for that machine."
	@echo ""
	@echo "Make Variables: (make ... VAR=VALUE)"
	@echo "  DIFF=1         show changes made"
	@echo "  CHECK=1      run in --check mode (implies DIFF=1)"

deps:
	.venv/bin/ansible-galaxy install -r requirements.yml

%:
	.venv/bin/ansible-playbook $@.yml $(CHECK_C) $(DIFF_C) $(DEBUG)
