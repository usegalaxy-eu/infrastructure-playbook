#!/usr/bin/env python
from bioblend import galaxy
import json
import time

with open('/etc/gx-api-creds.json', 'r') as handle:
    secrets = json.load(handle)

api_key = secrets['api_key']
url = secrets['url']
handlers = secrets['handlers']

history_name = "Nagios Run %s" % time.time()
gi = galaxy.GalaxyInstance(url, api_key)
history = gi.histories.create_history(name=history_name)
history_id = history['id']

jobs = []

# Run all of the jobs.
try:
    for handler in handlers:
        job = gi.tools.run_tool(history_id, 'echo_main_' + handler, {'echo': handler})
        jobs.append({
            'handler': handler,
            'job': job,
            'started': time.time()
        })

    # Check all the jobs
    for i in range(20):
        states = []
        for job in jobs:
            state = gi.jobs.get_state(job['job']['jobs'][0]['id'])
            states.append(state)
            if state in ('ok', 'error') and 'finished' not in job:
                job['finished'] = time.time()

        if all([state in ('ok', 'error') for state in states]):
            break

        # Otherwies we run until we hit end of range
        time.sleep(2)

    # Final states.
    for job in jobs:
        job['final_state'] = gi.jobs.get_state(job['job']['jobs'][0]['id'])
        if 'finished' not in job:
            job['finished'] = time.time()

    # Now we're done, output something useful.
    for job in jobs:
        print(secrets['galaxy_test_name'] + ".services,service=%s request_time=%s,status=%s" % (
            job['handler'],
            job['finished'] - job['started'],
            0 if job['final_state'] == 'ok' else 1
        ))

except Exception as e:
    gi.histories.delete_history(history_id, purge=True)
    # Just fail all handlers, something is up, leave it up to the admin to figure out.
    for handler in handlers:
        print(secrets['galaxy_test_name'] + ".services,service=%s request_time=60,status=1")

# Cleanup histories
gi.histories.delete_history(history_id, purge=True)
