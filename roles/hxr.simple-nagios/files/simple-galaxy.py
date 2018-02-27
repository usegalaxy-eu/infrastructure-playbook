#!/usr/bin/env python
from bioblend import galaxy
import time

api_key = open('/etc/gx-api-creds.txt', 'r').read().strip()
url = "https://usegalaxy.eu"

handlers = [
    "handler0",
    "handler1",
    "handler2",
    "handler3",
    "handler4",
    "handler5",
    "handler6",
    "handler7",
    "handler8",
    "handler9",
    "handler10",
    "handler11",
    "drmaa",
    "condor"
]

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
        print("eu.usegalaxy.services,service=%s request_time=%s,status=%s" % (
            job['handler'],
            job['finished'] - job['started'],
            0 if job['final_state'] == 'ok' else 1
        ))

except Exception as e:
    gi.histories.delete_history(history_id, purge=True)
