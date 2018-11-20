#!{{ statslurp_venv_dir }}/bin/python
import yaml
import argparse
import datetime
import hashlib

import psycopg2
from influxdb import InfluxDBClient

secrets = yaml.load(open('secret.yml', 'r'))
SALT = secrets['salt']
TOP_USAGE_LIMIT = 30
PGCONNS = secrets['pgconn']


parser = argparse.ArgumentParser(description="Translate Galaxy DB stats from PostgreSQL to InfluxDB")
parser.add_argument('instance', default='main', help="Galaxy instance")
parser.add_argument('--action', choices=('totals', 'daily'), help="Collect current totals or daily values for a past date (e.g. to backfill or as part of normal usage.)")
parser.add_argument('--date', help="Day to calculate statistics for, yyyy-mm-dd format please.")
args = parser.parse_args()
pconn_str = PGCONNS[args.instance]
time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def measure(metric, values, tags=None, time_override=None):
    m = {
        'measurement': metric,
        'time': time_override if time_override is not None else time,
        'fields': values,
    }
    if tags:
        m['tags'] = tags
    return m


def query(sql):
    pconn = psycopg2.connect(pconn_str)
    pc = pconn.cursor()
    pc.execute(sql)
    for row in pc:
        yield row
    pconn.close()


USER_QUERY = """
SELECT
    active, external, deleted, purged, count(*) as count
FROM
    galaxy_user
WHERE
    true {date_filter}
GROUP BY
    active, external, deleted, purged
"""

USER_QUERY_CUMULATIVE_SUM = """
SELECT
    count(*)
FROM
    galaxy_user
WHERE
    true {date_filter}
"""

TOP_GROUPS = """
SELECT
    galaxy_group.name, count(*)
FROM
    galaxy_group, user_group_association
WHERE
    user_group_association.group_id = galaxy_group.id
GROUP BY name
"""


DATASET_INFO_QUERY = """
SELECT
    state, deleted, purged, object_store_id, count(*), coalesce(sum(total_size), 0)
FROM
    dataset
GROUP BY
    state, deleted, purged, object_store_id;
"""

HDA_INFO_QUERY = """
SELECT
    history_dataset_association.extension, history_dataset_association.deleted,
    coalesce(sum(dataset.file_size), 0),
    coalesce(avg(dataset.file_size), 0),
    coalesce(min(dataset.file_size), 0),
    coalesce(max(dataset.file_size), 0),
    count(*)
FROM
    history_dataset_association, dataset
WHERE
    history_dataset_association.dataset_id = dataset.id {date_filter}
GROUP BY
    history_dataset_association.extension, history_dataset_association.deleted
"""

COLLECTION_INFO_QUERY = """
SELECT
    dc.collection_type, count(*)
FROM
    history_dataset_collection_association as hdca inner join dataset_collection as dc on hdca.dataset_collection_id = dc.id
GROUP BY
    dc.collection_type;
"""

TS_REPOS_QUERY = """
SELECT
    tool_shed, owner, count(*)
FROM
    tool_shed_repository
GROUP BY
    tool_shed, owner;
"""

# UNUSED, this is done sufficiently in user_disk_query
HISTORY_USER_QUERY = """
SELECT
    user_id, count(*)
FROM
    history
WHERE user_id is not null
GROUP BY
    user_id;
"""

HISTORY_INFO_QUERY = """
SELECT
    deleted, purged, published, importable, importing, genome_build, count(*)
FROM history
WHERE
    user_id IS NOT NULL {date_filter}
GROUP BY
    deleted, purged, published, importable, importing, genome_build;
"""

USER_DISK_QUERY = """
SELECT
    history.user_id, coalesce(sum(dataset.file_size), 0), coalesce(count(dataset.id), 0), coalesce(count(history.id), 0)
FROM
    history, history_dataset_association, dataset
WHERE
    history.id = history_dataset_association.history_id AND
    history_dataset_association.dataset_id = dataset.id
GROUP BY
    history.user_id;
"""

JOB_INFO_QUERY = """
SELECT
    state, job_runner_name, destination_id, count(*)
FROM
    job
WHERE
    user_id IS NOT NULL {date_filter}
GROUP BY
    state, job_runner_name, destination_id;
"""

JOB_QUERY_CUMULATIVE_SUM = """
SELECT
    count(*)
FROM
    job
WHERE
    true {date_filter}
"""

WORKFLOW_INFO_QUERY = """
SELECT
    deleted, importable, published, count(*)
FROM
    stored_workflow
WHERE
    true {date_filter}
GROUP BY
    deleted, importable, published;
"""

WORKFLOW_INVOKE_INFO_QUERY = """
SELECT
    scheduler, handler, count(*)
FROM
    workflow_invocation
WHERE
    true {date_filter}
GROUP BY
    scheduler, handler;
"""

def queries():
    for row in query(USER_QUERY.format(date_filter="")):
        yield measure('user_metadata', {'count': int(row[4])}, tags={'active': row[0], 'external': row[1], 'deleted': row[2], 'purged': row[3]})
    for row in query(TOP_GROUPS):
        yield measure('user_groups', {'count': int(row[1])}, tags={'group_name': row[0]})
    for row in query(DATASET_INFO_QUERY):
        yield measure('datasets', {'count': int(row[4]), 'size': int(row[5])}, tags={'state': row[0], 'deleted': row[1], 'purged': row[2], 'object_store': row[3]})
    for row in query(HDA_INFO_QUERY.format(date_filter="")):
        yield measure('hda.meta', {'sum': int(row[2]), 'avg': int(row[3]), 'min': int(row[4]), 'max': int(row[5]), 'count': int(row[6])},
                      tags={'extension': row[0], 'deleted': row[1]})
    for row in query(COLLECTION_INFO_QUERY):
        yield measure('collection', {'count': int(row[1])}, tags={'type': row[0]})
    for row in query(TS_REPOS_QUERY):
        yield measure('toolshed_repositories', {'count': int(row[2])}, tags={'tool_shed': row[0], 'owner': row[1]})
    for row in query(USER_DISK_QUERY):
        yield measure('user_disk', {'datasets': int(row[2]), 'histories': int(row[3]), 'disk_usage': int(row[1])}, tags={'user_id': row[0]})
    for row in query(HISTORY_INFO_QUERY.format(date_filter="")):
        yield measure('histories', {'count': int(row[6])}, tags={'deleted': row[0], 'purged': row[1], 'published': row[2], 'importable': row[3], 'importing': row[4], 'genome_build': row[5]})
    for row in query(JOB_INFO_QUERY.format(date_filter="")):
        yield measure('jobs', {'count': int(row[3])}, tags={'state': row[0], 'job_runner_name': row[1], 'destination_id': row[2]})
    for row in query(WORKFLOW_INFO_QUERY.format(date_filter="")):
        yield measure('workflows', {'count': int(row[3])}, tags={'deleted': row[0], 'importable': row[1], 'published': row[2]})
    for row in query(WORKFLOW_INVOKE_INFO_QUERY.format(date_filter="")):
        yield measure('workflow_invocations', {'count': int(row[2])}, tags={'scheduler': row[0], 'handler': row[1]})



def per_day(date):
    """
    queries of things where we want to see trends over time. It should receive
    a valid date ***THAT IS ALREADY OVER***.

    date should be a str of yyyy-mm-dd
    """
    date_filter = """
    AND date_trunc('day', create_time) = '{date}'::date
    """.format(date=date)

    prev_filter = """
    AND date_trunc('day', create_time) <= '{date}'::date
    """.format(date=date)

    # Oh this *so* isn't TZ compat, is it. Well.... whatever. We'll submit it
    # for 3 am and hope for the best that we don't land on a hour shift
    # back/forwards.
    fmt_date = date + 'T03:00:00Z'

    for row in query(USER_QUERY.format(date_filter=date_filter)):
        yield measure('users.daily', {'count': int(row[4])}, tags={'active': row[0], 'external': row[1], 'deleted': row[2], 'purged': row[3]}, time_override=fmt_date)
    for row in query(HISTORY_INFO_QUERY.format(date_filter=date_filter)):
        yield measure('histories.daily', {'count': int(row[6])}, tags={'deleted': row[0], 'purged': row[1], 'published': row[2], 'importable': row[3], 'importing': row[4], 'genome_build': row[5]}, time_override=fmt_date)
    for row in query(HDA_INFO_QUERY.format(date_filter=date_filter.replace('create_time', 'history_dataset_association.create_time'))):
        yield measure('hda.meta.daily', {'sum': int(row[2]), 'avg': int(row[3]), 'min': int(row[4]), 'max': int(row[5]), 'count': int(row[6])},
                      tags={'extension': row[0], 'deleted': row[1]}, time_override=fmt_date)
    for row in query(JOB_INFO_QUERY.format(date_filter=date_filter)):
        yield measure('jobs.daily', {'count': int(row[3])}, tags={'state': row[0], 'job_runner_name': row[1], 'destination_id': row[2]}, time_override=fmt_date)

    # Cumulative sums over all previous values
    for row in query(USER_QUERY_CUMULATIVE_SUM.format(date_filter=prev_filter)):
        yield measure('users.prev', {'count': int(row[0])}, time_override=fmt_date)
    for row in query(JOB_QUERY_CUMULATIVE_SUM.format(date_filter=prev_filter)):
        yield measure('jobs.prev', {'count': int(row[0])}, time_override=fmt_date)

    for row in query(WORKFLOW_INFO_QUERY.format(date_filter=date_filter)):
        yield measure('workflows.daily', {'count': int(row[3])}, tags={'deleted': row[0], 'importable': row[1], 'published': row[2]}, time_override=fmt_date)
    for row in query(WORKFLOW_INVOKE_INFO_QUERY.format(date_filter=date_filter)):
        yield measure('workflow_invocations.daily', {'count': int(row[2])}, tags={'scheduler': row[0], 'handler': row[1]}, time_override=fmt_date)

    # These are more overlal health / report types that I don't know what to do with
    # query = """
        # SELECT 'https://usegalaxy.eu/u/' || galaxy_user.username || '/w/' || stored_workflow.slug as url, count(*)
        # FROM workflow, stored_workflow, galaxy_user
        # WHERE workflow.stored_workflow_id = stored_workflow.id AND stored_workflow.published = true AND galaxy_user.id = stored_workflow.user_id
        # GROUP BY url ORDER BY count DESC LIMIT 10;
    # """


client = InfluxDBClient(**secrets['influxdb'])
# client.create_database(secrets['influxdb']['database'])

if args.action == 'totals':
    client.write_points(queries())
else:
    #for p in per_day(args.date): print(p)
    client.write_points(per_day(args.date))
