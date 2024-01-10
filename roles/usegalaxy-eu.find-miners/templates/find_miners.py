#!/usr/bin/env python
# A command line script that iterates over the currently running jobs and stops them as well as logs the user,
# when a file in the JWD matches to a list of hashes

import argparse
import os
import pathlib
import sys
import time

import galaxy_jwd
from tqdm import tqdm

CHECKSUM_FILE_ENV = "MALWARE_CHECKSUM_FILE"


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


class Job:
    def __init__(
        self,
        galaxy_id: int,
        object_store_id: int,
        user_id: int,
        tool_id: str,
        job_runner_name: str,
        jwd=None,
    ) -> None:
        self.galaxy_id = galaxy_id
        self.object_store_id = object_store_id
        self.jwd = jwd
        self.user_id = user_id
        self.tool_id = tool_id
        self.job_runner_name = job_runner_name


class Malware:
    """
    Loads a yaml with the following schema
        ---
        class:
          name:
            version:
              severity: [high, medium, low]
              description: "optional info"
              checksums:
                crc32: <checksum crc32>
                sha1: <checksum sha1>
    """

    def __init__(
        self,
        malware_class: str,
        name: str,
        version: str,
        severity: str,
        description: str,
        crc32: str,
        sha1: str,
    ) -> None:
        self.malware_class = malware_class
        self.name = name
        self.version = version
        self.severity = severity
        self.description = description
        self.crc32 = crc32
        self.sha1 = sha1


def load_malware_info_from_env(env=CHECKSUM_FILE_ENV) -> dict:
    if not os.environ.get(env):
        raise ValueError(env)
    malware_info = os.environ.get(env).strip()
    return malware_info


def construct_malware_list(malware: dict) -> [Malware]:
    malware_list = []
    for malware_class in malware:
        for pkg in malware[malware_class]:
            for version in malware[malware_class][pkg]:
                malware_list.append(
                    Malware(
                        malware_class=malware_class,
                        name=pkg,
                        version=version,
                        severity=malware[malware_class][pkg][version][
                            "severity"
                        ],
                        description=malware[malware_class][pkg][version][
                            "description"
                        ],
                        crc32=malware[malware_class][pkg][version][
                            "checksums"
                        ]["crc32"],
                        sha1=malware[malware_class][pkg][version]["checksums"][
                            "sha1"
                        ],
                    )
                )
    return malware_list


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

        object_store_conf = galaxy_jwd.get_object_store_conf_path(
            galaxy_config_file
        )
        backends = galaxy_jwd.parse_object_store(object_store_conf)

        # Add pulsar staging directory (runner: pulsar_embedded) to backends
        backends["pulsar_embedded"] = galaxy_jwd.get_pulsar_staging_dir(
            galaxy_pulsar_app_conf
        )
        self.backends = backends

    # might deserve it's own function in galaxy_jwd.py
    def get_jwd_path(self, job: Job):
        jwd = galaxy_jwd.decode_path(
            job.galaxy_id,
            [job.object_store_id],
            self.backends,
            job.job_runner_name,
        )
        return jwd


class RunningJobDatabase(galaxy_jwd.Database):
    def __init__(self):
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
        db_password = galaxy_jwd.extract_password_from_pgpass(
            pgpass_file=os.path.expanduser("~/.pgpass")
        )
        super().__init__(
            db_name,
            db_user,
            db_host,
            db_password,
        )

    def get_running_jobs(self, tool=None) -> [Job]:
        query = f"""
                SELECT id, object_store_id, tool_id, user_id, job_runner_name
                FROM job
                WHERE state = 'running'
                AND object_store_id IS NOT NULL
                AND user_id IS NOT NULL
            """
        cur = self.conn.cursor()
        if len(tool) > 0:
            query += f"AND tool_id LIKE '%{tool}%'"
        cur.execute(query + ";")
        running_jobs = cur.fetchall()
        cur.close()
        self.conn.close()
        print(running_jobs)
        # Create a dictionary with job_id as key and object_store_id, and
        # update_time as values
        if not running_jobs:
            print(
                f"No running jobs with tool_id like {tool} found.",
                file=sys.stderr,
            )
            sys.exit(1)
        running_jobs_list = []
        for (
            job_id,
            object_store_id,
            tool_id,
            user_id,
            job_runner_name,
        ) in running_jobs:
            running_jobs_list.append(
                Job(
                    galaxy_id=job_id,
                    object_store_id=object_store_id,
                    tool_id=tool_id,
                    user_id=user_id,
                    job_runner_name=job_runner_name,
                )
            )
        return running_jobs_list


def main():
    """
    Miner Finder's main function. Shows a status bar while processing the jobs found in Galaxy
    """
    args = make_parser().parse_args()
    print(args.tool + "1")
    jwd_getter = JWDGetter()
    db = RunningJobDatabase()
    jobs = db.get_running_jobs(args.tool)
    for job in tqdm(jobs, desc="Processing jobs…", ascii=False, ncols=75):
        time.sleep(0.01)
        # print(f"processing Job{i} of ")

        jwd_path = jwd_getter.get_jwd_path(job)
        if pathlib.Path(jwd_path).exists():
            jwd_path = pathlib.Path(jwd_path)

        else:
            print(
                f"JWD for Job {job.galaxy_id} found but does not exist in FS",
                file=sys.stderr,
            )

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
