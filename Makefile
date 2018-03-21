LAUNCH_VM := 0

help:
	@echo "Run 'make [grafana|jenkins|haproxy|...]' to re-run ansible for that machine. Supply LAUNCH_VM=1 to launch a VM as well."

clean:
	@rm -f *.retry

%:
  ifeq ($(LAUNCH_VM), 1)
	ansible-playbook -i hosts $@_vm.yml --vault-password-file .vault_password
  endif
	ansible-playbook -i hosts $@.yml --vault-password-file .vault_password
