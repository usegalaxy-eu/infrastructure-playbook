#!{{ statslurp_venv_dir }}/bin/python
import yaml
import argparse
import datetime

import psycopg2
from influxdb import InfluxDBClient

secrets = yaml.load(open('secret.yml', 'r'))
SALT = secrets['salt']
TOP_USAGE_LIMIT = 30
PGCONNS = secrets['pgconn']

time = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')


def queue_monitor_v2():
    return """
        SELECT
            tool_id, tool_version, destination_id, handler, state, job_runner_name, count(*) as count
        FROM job
        WHERE
            state = 'running' or state = 'queued'
        GROUP BY
            tool_id, tool_version, destination_id, handler, state, job_runner_name;
    """


def make_measurement(measurement, value, tags=None):
    m = {
        'measurement': measurement,
        'time': time,
        'fields': {
            'value': value
        }
    }
    if tags:
        m['tags'] = tags
    return m


def pg_execute(pconn_str, sql):
    pconn = psycopg2.connect(pconn_str)
    pc = pconn.cursor()
    pc.execute(sql)
    for row in pc:
        yield row
    pconn.close()


def collect(instance):
    measurements = []
    pconn_str = PGCONNS[instance]
    for row in pg_execute(pconn_str, queue_monitor_v2()):
        tags = {
            'tool': row[0],
            'tool_version': row[1],
            'destination': row[2],
            'handler': row[3],
            'state': row[4],
            'cluster': row[5],
        }
        measurements.append(make_measurement('job_queue', float(row[6]), tags=tags))

    return measurements


def dump(instance, points):
    client = InfluxDBClient(**secrets['influxdb'])
    # client.create_database(secrets['influxdb']['database'])
    client.write_points(points)


def main():
    parser = argparse.ArgumentParser(description="Translate Galaxy DB stats from PostgreSQL to InfluxDB")
    parser.add_argument('instance', default='main', help="Galaxy instance")
    args = parser.parse_args()
    points = collect(args.instance)
    dump(args.instance, points)


if __name__ == '__main__':
    main()
