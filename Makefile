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
	@echo "  LAUNCH_VM=1    launch a VM as well"
	@echo "  DIFF=1         show changes made"
	@echo "  CHECK=1      run in --check mode (implies DIFF=1)"

clean:
	@rm -f *.retry

%:
  ifeq ($(LAUNCH_VM), 1)
	ansible-playbook -i hosts $@_vm.yml --vault-password-file .vault_password $(CHECK_C) $(DIFF_C) $(DEBUG)
  endif
	ansible-playbook -i hosts $@.yml --vault-password-file .vault_password $(CHECK_C) $(DIFF_C) $(DEBUG)
