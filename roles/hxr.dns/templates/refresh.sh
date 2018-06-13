#!/bin/bash
certbot certonly \
	--expand \
	--no-eff-email \
	--preferred-challenges http-01 \
	--http-01-port 8118 \
	{% for domain in server_names %}
	-d {{ domain }} \
	{% endfor %}
	{% for domain in server_names_de %}
	-d {{ domain }} \
	{% endfor %}
	--standalone \
	--agree-tos \
	-m security@usegalaxy.eu
