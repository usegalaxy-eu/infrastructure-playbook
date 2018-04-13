LAUNCH_VM := 0
ifdef DRY_RUN
  DRY_RUN_C := --check --diff
else
  DRY_RUN_C := 
endif


help:
	@echo "Run 'make [grafana|jenkins|haproxy|...]' to re-run ansible for that machine."
	@echo ""
	@echo "Make Variables: (make ... VAR=VALUE)"
	@echo "  LAUNCH_VM=1    launch a VM as well"
	@echo "  DRY_RUN=1      run in --check mode"

clean:
	@rm -f *.retry

%:
  ifeq ($(LAUNCH_VM), 1)
	ansible-playbook -i hosts $@_vm.yml --vault-password-file .vault_password $(DRY_RUN_C)
  endif
	ansible-playbook -i hosts $@.yml --vault-password-file .vault_password $(DRY_RUN_C)
