# Postfix relay

Deploy with `ansible-playbook -i hosts postfix.yml`. Deployment settings are in
`group_vars/maintenance.yml`; credentials are supplied through vaulted variables.

## Delivery transports

Postfix uses shared persistent queue storage with independent transport scheduling:

| Envelope sender | Transport | Deployment pacing |
| --- | --- | --- |
| Addresses in `postfix_bulk_senders` | `bulk` | 6s delay (~600 messages/hour), concurrency limit 2 |
| Null sender (`<>`, delivery-status notifications) | `dsnrelay` | No rate delay, concurrency limit 2 |
| All other external mail, including regular Galaxy email | `smtp` | 36s delay (~100 messages/hour), concurrency limit 2 |

Routing uses SMTP `MAIL FROM`, not the visible `From` header. Campaign submission
must use a distinct envelope sender; Galaxy's global `email_from` does not
automatically distinguish campaign notifications from regular notifications.
The configured campaign sender must also be authorized by the upstream provider.

The queue manager reads transport-specific delays and concurrency limits from
`main.cf`. The custom SMTP delivery services in `master.cf` inherit the upstream
SASL and TLS settings. Log prefixes distinguish `postfix/bulk/smtp` and
`postfix/dsnrelay/smtp` from regular `postfix/smtp` deliveries.

Together the paced transports target approximately 700 single-recipient
deliveries/hour (600 bulk plus 100 regular). Bounces are additional and unpaced.
They share one upstream account: the combined traffic, including bounces, is
still subject to that account's recipient limit and the source host's connection
and authentication limits. A delivery delay is not a strict recipient quota.

## Verification after deployment

On maintenance, inspect the map (use `hash:` instead if that type was selected):

```bash
postmap -q assumetest-no-reply@informatik.uni-freiburg.de lmdb:/etc/postfix/sender_transport
postmap -q '<>' lmdb:/etc/postfix/sender_transport
postmap -q galaxy-no-reply@informatik.uni-freiburg.de lmdb:/etc/postfix/sender_transport
postconf smtp_destination_rate_delay bulk_destination_rate_delay dsnrelay_destination_rate_delay
postconf -M bulk/unix dsnrelay/unix
postfix check
```

Expected map results are `bulk:`, `dsnrelay:`, and no match (default `smtp`).
From sn09, submit several single-recipient test messages using the campaign
envelope sender, then submit one using Galaxy's regular sender. Check
`/var/log/maillog`: campaign deliveries should be spaced by approximately six
seconds and regular deliveries by approximately 36 seconds. Regular mail should
use its independent transport rather
than wait for the campaign to finish. Confirm `status=sent` and inbox receipt.

Unchanged daily playbook runs do not rebuild the routing database or restart
Postfix. Changes to the sender map, transport configuration, or other managed
configuration trigger the restart handler. Temporary failures remain queued
for the configured lifetime; permanent SMTP rejections generate bounces.
