#!/usr/bin/env python
# A command line script that iterates over the currently running jobs and stops them as well as logs the user,
# when a file in the JWD matches to a list of hashes

import galaxy_jwd as jwd
import argparse
import pathlib
from tqdm import tqdm
import time
import os


def make_parser() -> argparse.ArgumentParser:
    my_parser = argparse.ArgumentParser(
        prog="Miner Finder",
        description="""
                Takes paths to CRC32 and (optionally) SHA1 hashfiles as arguments,
                searches in currently used JWDs for matching files
                and stops or reports the jobs and users.


            The following ENVs (same as gxadmin's) should be set:
                GALAXY_CONFIG_FILE: Path to the galaxy.yml file
                GALAXY_LOG_DIR: Path to the Galaxy log directory
                PGDATABASE: Name of the Galaxy database
                PGUSER: Galaxy database user
                PGHOST: Galaxy database host

            We also need a ~/.pgpass file (same as gxadmin's) in format:
                <pg_host>:5432:*:<pg_user>:<pg_password>
            """,
    )

    my_parser.add_argument(
        "crc32",
        help="Path to a CRC32 checksum file",
        nargs="+",
        type=argparse.FileType("r"),
    )

    my_parser.add_argument(
        "--sha1",
        help="Path to an additional SHA1 checksum file (optional for more precision). \
            SHA1 is only calculated when CRC32 matches",
        nargs="+",
        type=argparse.FileType("r"),
    )

    my_parser.add_argument(
        "--remove-jobs",
        action="store_true",
        help="Removes the jobs from condor and fails them in Galaxy",
    )

    my_parser.add_argument(
        "--block-users",
        help="CAUTION: \
            This flag automatically removes users owning matching jobs using Bioblend!",
        metavar="GALAXY_CRED_FILE",
        type=argparse.FileType("r"),
    )

    my_parser.add_argument(
        "--min-size",
        metavar="MIN_SIZE_MB",
        help="Minimum filesize im MB to limit the files to scan.",
        type=int,
    )

    my_parser.add_argument(
        "--max-size",
        metavar="MAX_SIZE_MB",
        help="Maximum filesize im MB to limit the files to scan. \
            CAUTION: Not setting this value can lead to very long computation times",
        type=int,
    )

    my_parser.add_argument(
        "--since", help="Access time in hours backwards from now", type=int
    )

    my_parser.add_argument(
        "--tool",
        help="A string to filter tools in the tool_id column of currently running jobs. \
            Use like 'grep' after the gxadmin query queue-details command.",
        type=str,
        default="",
    )
    return my_parser


# might deserve it's own function in galaxy_jwd.py
def setup_db_connection() -> jwd.Database:
    if not os.environ.get("PGDATABASE"):
        raise ValueError("Please set ENV PGDATABASE")
    db_name = os.environ.get("PGDATABASE").strip()

    if not os.environ.get("PGUSER"):
        raise ValueError("Please set ENV PGUSER")
    db_user = os.environ.get("PGUSER").strip()

    if not os.environ.get("PGHOST"):
        raise ValueError("Please set ENV PGHOST")
    db_host = os.environ.get("PGHOST").strip()

    # Check if ~/.pgpass file exists and is not empty
    if (
        not os.path.isfile(os.path.expanduser("~/.pgpass"))
        or os.stat(os.path.expanduser("~/.pgpass")).st_size == 0
    ):
        raise ValueError(
            "Please create a ~/.pgpass file in format: "
            "<pg_host>:5432:*:<pg_user>:<pg_password>"
        )
    db_password = jwd.extract_password_from_pgpass(
        pgpass_file=os.path.expanduser("~/.pgpass")
    )
    return jwd.Database(
        dbname=db_name, dbuser=db_user, dbhost=db_host, dbpassword=db_password
    )


class JWDGetter:
    """
    This class is a workaround for calling 'galaxy_jwd.py's main function.
    """

    def __init__(self) -> None:
        """
        Reads the storage backend configuration
        (might deserve it's own function in galaxy_jwd.py)
        """
        if not os.environ.get("GALAXY_CONFIG_FILE"):
            raise ValueError("Please set ENV GALAXY_CONFIG_FILE")
        galaxy_config_file = os.environ.get("GALAXY_CONFIG_FILE").strip()

        # Check if the given galaxy.yml file exists
        if not os.path.isfile(galaxy_config_file):
            raise ValueError(
                f"The given galaxy.yml file {galaxy_config_file} does not exist"
            )
        if not os.environ.get("GALAXY_PULSAR_APP_CONF"):
            raise ValueError("Please set ENV GALAXY_PULSAR_APP_CONF")
        galaxy_pulsar_app_conf = os.environ.get(
            "GALAXY_PULSAR_APP_CONF"
        ).strip()

        object_store_conf = jwd.get_object_store_conf_path(galaxy_config_file)
        backends = jwd.parse_object_store(object_store_conf)

        # Add pulsar staging directory (runner: pulsar_embedded) to backends
        backends["pulsar_embedded"] = jwd.get_pulsar_staging_dir(
            galaxy_pulsar_app_conf
        )
        self.backends = backends

    # might deserve it's own function in galaxy_jwd.py
    def get_jwd_path(self, job_id: int, db: jwd.Database):
        object_store_id, job_runner_name = db.get_job_info(job_id)
        jwd_path = pathlib.Path(
            jwd.decode_path(
                job_id, [object_store_id], self.backends, job_runner_name
            )
        )
        if pathlib.Path(jwd_path).exists():
            return jwd_path


class Job:
    def __init__(
        self,
        galaxy_id: int,
        condor_id: int,
        jwd: pathlib.Path,
        owner: str,
        owner_id: int,
    ) -> None:
        galaxy_id = galaxy_id
        condor_id = condor_id
        jwd = jwd
        owner = owner
        owner_id = owner_id


def get_running_jobs(self, tool: str) -> [Job]:
    cur = self.conn.cursor()
    cur.execute(
        f"""
            SELECT id, object_store_id, user
            FROM job
            WHERE state = 'running'
            AND tool_id LIKE '%{tool}%'
            AND object_store_id IS NOT NULL
            """
    )
    failed_jobs = cur.fetchall()
    cur.close()
    self.conn.close()

    # Create a dictionary with job_id as key and object_store_id, and
    # update_time as values
    failed_jobs_dict = {}
    for job_id, object_store_id, update_time in failed_jobs:
        failed_jobs_dict[job_id] = [object_store_id, update_time]

    if not failed_jobs_dict:
        print(
            f"No failed jobs older than {days} days found.",
            file=sys.stderr,
        )
        sys.exit(1)

    return failed_jobs_dict


def main():
    """
    Miner Finder's main function. Shows a status bar while processing the jobs found in Galaxy
    """
    args = make_parser().parse_args()
    jobs = 100
    db = setup_db_connection()
    db.get_running_jobs
    jobs = db.get_running_jobs(args.tool)
    for i in tqdm(range(jobs), desc="Processing jobs…", ascii=False, ncols=75):
        time.sleep(0.01)
        # print(f"processing Job{i} of ")

    print("Complete.")


# get a list of Galaxy IDs of currently running interactive jobs
# for each job
# get a list of all files (recursively) smaller than 10MB in that JWD using change_to_jwd.py
# for each file
# hash that file with crc32
# compare hash to given list of hashes provided and if it matches,
# also hash with md5 and if that matches
# - extract the condor_id from file
# - gxadmin mutate fail-job $job
# - gxadmin report job-info $job
# - condor rm $condor_id
# - gxadmin report job-info | grep Owner

# extended and when tested:
# implement auto block with bioblend

if __name__ == "__main__":
    main()
