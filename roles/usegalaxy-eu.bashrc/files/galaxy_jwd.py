#!/usr/bin/env python
"""Print path of or clean up Galaxy job working directories (JWDs).

Required environment variables:
    PYTHONPATH:         path to the Galaxy code (needed to `import galaxy`)
    GALAXY_CONFIG_FILE: path to the galaxy.yml file
    GALAXY_LOG_DIR:     path to the Galaxy log directory (clean only)

Optional environment variables:
    GALAXY_PULSAR_APP_CONF: path to the pulsar_app.yml file, needed to locate
        the staging directory of pulsar_embedded jobs; defaults to Galaxy's own
        default (<data_dir>/pulsar_staging)

The database connection is read from galaxy.yml (overridable with
GALAXY_CONFIG_OVERRIDE_DATABASE_CONNECTION, like Galaxy itself).

Uses the Galaxy model and object store (run with the Galaxy virtualenv) to
resolve JWD paths reusing the same logic Galaxy uses.
"""

import argparse
import os
import shutil
import sys
import textwrap
from datetime import datetime, timedelta, timezone

import yaml
from galaxy.config import GalaxyAppConfiguration
from galaxy.job_execution.setup import JobWorkingDirectory
from galaxy.model import Job, mapping
from galaxy.objectstore import build_object_store_from_config
from galaxy.util.properties import load_app_properties
from sqlalchemy import select


def parse_args():
    parser = argparse.ArgumentParser(
        prog="galaxy_jwd",
        description=(
            "Get the JWD path for a Galaxy job id or delete the JWDs of "
            "failed jobs."
        ),
    )

    operations = parser.add_subparsers(
        dest="operation",
        metavar="",  # do not use argparse metavars
        title="operations",
    )

    get_parser = operations.add_parser(
        "get",
        help="Print the JWD path of a job id",
        epilog=textwrap.dedent("""
            example:
                python galaxy_jwd.py get 12345678
        """),  # noqa: E501
    )
    get_parser.add_argument(
        "job_id",
        type=int,
        help="Galaxy job id",
    )

    clean_parser = operations.add_parser(
        "clean",
        help="Delete JWDs of failed jobs older than X days",
    )
    dry_run = clean_parser.add_mutually_exclusive_group(required=True)
    dry_run.add_argument(
        "--dry_run",
        action="store_true",
        help="Print the JWDs without deleting them",
    )
    dry_run.add_argument(
        "--no_dry_run",
        action="store_true",
        help="Delete the JWDs and log the deletions",
    )
    clean_parser.add_argument(
        "--days",
        type=int,
        default=5,
        help="Minimum job age in days (default: 5)",
    )

    return parser.parse_args(args=None if sys.argv[1:] else ["--help"])


def require_env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Please set ENV {name}")
    return value.strip()


def connect(config_file):
    """Connect to the Galaxy database and object store without a Galaxy app."""
    config = GalaxyAppConfiguration(
        config_file=config_file,
        override_tempdir=False,
        **load_app_properties(config_file=config_file),
    )
    model = mapping.init(
        config.file_path,
        config.database_connection,
        config.database_engine_options,
    )
    return config, model.session, build_object_store_from_config(config)


def pulsar_staging_dir(config):
    """Staging directory of embedded Pulsar jobs.

    Mirrors the default applied by galaxy.jobs.runners.pulsar when
    pulsar_app.yml does not define staging_directory. Their layout is
    <staging>/<job id>, without the hashed subdirectories.
    """
    conf = os.environ.get("GALAXY_PULSAR_APP_CONF")
    if conf and os.path.isfile(conf):
        with open(conf) as file:
            staging = (yaml.safe_load(file) or {}).get("staging_directory")
        if staging:
            return staging
    return os.path.join(config.data_dir, "pulsar_staging")


def jwd_path(job, config, object_store):
    """Return the existing JWD path of a job, or None.

    Delegates to JobWorkingDirectory, which resolves the path from
    `job.working_directory` (persisted from the job_working_directory
    destination param, e.g. by TPV) with fallback to the job_work extra_dir
    of the job's object store backend.
    """
    runner = job.job_runner_name or ""
    destination = job.destination_id or ""

    if runner.startswith("pulsar_embedded") or destination.startswith(
        "pulsar_embedded"
    ):
        path = os.path.join(pulsar_staging_dir(config), str(job.id))
    else:
        jwd = JobWorkingDirectory(job, object_store)
        path = jwd.resolve() if jwd.exists() else None

    if path and os.path.isdir(path):
        return path

    if path:
        print(f"Tried JWD candidate {path}, does not exist", file=sys.stderr)
    return None


def delete_jwd(path):
    try:
        print(f"Deleting JWD: {path}")
        shutil.rmtree(path)
    except OSError as e:
        print(f"Error deleting JWD: {path} : {e.strerror}")


def get(session, config, object_store, job_id):
    job = session.get(Job, job_id)
    if job is None:
        sys.exit(f"Job '{job_id}' was not found in the database")
    path = jwd_path(job, config, object_store)
    if path is None:
        sys.exit(f"ERROR: Job working directory (of {job_id}) does not exist")
    print(path)


def clean(session, config, object_store, log_dir, args):
    if not os.path.isdir(log_dir):
        sys.exit(f"The given Galaxy log directory {log_dir} does not exist")
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=args.days
    )
    jobs = session.scalars(
        select(Job).where(
            Job.state == Job.states.ERROR,
            Job.update_time.is_not(None),
            Job.update_time <= cutoff,
        )
    ).all()
    if not jobs:
        sys.exit(f"No failed jobs older than {args.days} days found.")
    found = [
        (j.id, p) for j in jobs if (p := jwd_path(j, config, object_store))
    ]
    if args.dry_run:
        for job_id, path in found:
            print(f"{job_id}: {path}")
        return
    log_file = os.path.join(
        log_dir,
        f"jwd_cleanup_{datetime.now().strftime('%d_%m_%Y-%I_%M_%S')}.log",
    )
    with open(log_file, "w") as log:
        log.write(
            "The following job working directories (JWDs) belonging to the "
            "failed jobs are deleted\nJob id: JWD path\n"
        )
        for job_id, path in found:
            delete_jwd(path)
            log.write(f"{job_id}: {path}\n")


def main():
    args = parse_args()
    config_file = require_env("GALAXY_CONFIG_FILE")
    if not os.path.isfile(config_file):
        sys.exit(f"The given galaxy.yml file {config_file} does not exist")
    config, session, object_store = connect(config_file)
    if args.operation == "get":
        get(session, config, object_store, args.job_id)
    else:
        clean(
            session, config, object_store, require_env("GALAXY_LOG_DIR"), args
        )


if __name__ == "__main__":
    main()
