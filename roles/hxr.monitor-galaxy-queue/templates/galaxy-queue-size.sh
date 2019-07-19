#!/bin/bash
export PGUSER={{ postgres_user }}
export PGHOST={{ postgres_host }}
GDPR_MODE=1 gxadmin iquery queue-overview --short-tool-id
gxadmin iquery workflow-invocation-status
