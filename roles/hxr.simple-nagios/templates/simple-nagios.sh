#!/usr/bin/env bash
. /usr/bin/simple-nagios-library

{% if galaxy_nagios_urls.http_tests %}
{% for c in galaxy_nagios_urls.http_tests %}
expect_http {{ c.name }} {{ c.url }} {{ c.code }}
{% endfor %}
{% endif %}

{% if galaxy_nagios_urls.ftp_tests %}
{% for c in galaxy_nagios_urls.ftp_tests %}
expect_ftps {{ c.name }} {{ c.url }}
{% endfor %}
{% endif %}

{% if galaxy_nagios_urls.ftp_age_tests %}
{% for c in galaxy_nagios_urls.ftp_age_tests %}
expect_gx_ftp_age {{ c.name }} {{ c.url }}
{% endfor %}
{% endif %}
