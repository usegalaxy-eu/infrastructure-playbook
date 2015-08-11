#!/usr/bin/env python
###
### This file is managed by Ansible.  ALL CHANGES WILL BE OVERWRITTEN.
###

import re
import sys
import datetime
import smtplib
from email.mime.text import MIMEText

yesterday = datetime.date.today() - datetime.timedelta(days=1)
md = '%s ' % yesterday.strftime('%b %d')
recmp = re.compile(' ([\w-]+) post from (.*) discarded: SpamAssassin score was ([[\d\.]+) ')

out = {}
for f in ( open('/var/log/mailman/vette.1'), open('/var/log/mailman/vette') ):
    for line in f:
        if not line.startswith(md):
            continue
        match = re.search(recmp, line)
        if match:
            mlist = match.group(1)
            sender = match.group(2)
            score = match.group(3)
            if mlist not in out:
                out[mlist] = {}
            if sender not in out[mlist]:
                out[mlist][sender] = [ score ]
            else:
                out[mlist][sender].append( [ score ] )

if out:
    body = 'Auto-discard report\n'
    body += 'sender: score(s)\n\n'

    for mlist in sorted(out.keys()):
	body += mlist
	body += '\n'
	body += '-' * len(mlist)
	body += '\n'
	for sender in sorted(out[mlist].keys()):
	    body += sender
	    body += ': '
	    body += ', '.join(sorted(out[mlist][sender]))
	    body += '\n'
	body += '\n'

    msg = MIMEText(body)
    msg['Subject'] = 'Galaxy mailing list auto-discards: %s' % yesterday.strftime('%Y/%m/%d')
    msg['From'] = 'Galaxy Mailman <mailman@lists.galaxyproject.org>'
    msg['To'] = 'List Admins <galaxy-bugs-owner@lists.galaxyproject.org>'

    s = smtplib.SMTP('localhost')
    s.sendmail('mailman@lists.galaxyproject.org', ['galaxy-bugs-owner@lists.galaxyproject.org'], msg.as_string())
    s.quit()

sys.exit(0)
