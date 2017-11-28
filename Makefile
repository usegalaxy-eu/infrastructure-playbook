clean:
	@rm -f *.retry

ftp:
	ansible-playbook -i hosts ftp_vm.yml --vault-password-file ~/.vault_pass.txt
	ansible-playbook -i hosts ftp.yml --vault-password-file ~/.vault_pass.txt

haproxy:
	ansible-playbook -i hosts haproxy_vm.yml --vault-password-file ~/.vault_pass.txt
	ansible-playbook -i hosts haproxy.yml --vault-password-file ~/.vault_pass.txt

gitlab:
	ansible-playbook -i hosts gitlab_vm.yml --vault-password-file ~/.vault_pass.txt
	ansible-playbook -i hosts gitlab.yml --vault-password-file ~/.vault_pass.txt

pgs:
	ansible-playbook -i hosts pgs.yml --vault-password-file ~/.vault_pass.txt
