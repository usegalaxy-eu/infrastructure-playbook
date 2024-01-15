#!/usr/bin/env python
# A command line script that iterates over the currently running jobs and stops them as well as logs the user,
# when a file in the JWD matches to a list of hashes

import argparse
import datetime
import hashlib
import os
import pathlib
import sys
import time
import zlib

import galaxy_jwd
import yaml
from tqdm import tqdm

CHECKSUM_FILE_ENV = "MALWARE_LIB"

CURRENT_TIME = int(time.time())


def convert_arg_to_byte(mb: str) -> int:
    return int(mb) << 20


def convert_arg_to_seconds(hours: str) -> int:
    return int(hours) * 60 * 60


def make_parser() -> argparse.ArgumentParser:
    my_parser = argparse.ArgumentParser(
        prog="Miner Finder",
        description="""
            Loads a yaml malware library with CRC32 and SHA1 hashes as arguments
            from the environment variable "MALWARE_LIB",
            searches in JWDs of currently running jobs for matching files
            and reports jobs, users and malware details if specified.
            Malware library file has the following schema:
                class:
                    name:
                        version:
                            severity: [high, medium, low]
                            description: "optional info"
                            checksums:
                                crc32: <checksum crc32, gzip algorithm, integer representation>
                                sha1: <checksum sha1, hex representation>
            WARNING:
            Be careful with how you generate the CRC32 hashes:
            There are multiple algorithms, this script is using the one specified by IEEE 802.3
            You should get this when using the gzip command on POSIX systems
            and convert it to integer representation.

            The following ENVs (same as gxadmin's) should be set:
                GALAXY_CONFIG_FILE: Path to the galaxy.yml file
                GALAXY_LOG_DIR: Path to the Galaxy log directory
                PGDATABASE: Name of the Galaxy database
                PGUSER: Galaxy database user
                PGHOST: Galaxy database host

            We also need a ~/.pgpass file (same as gxadmin's) in format:
                <pg_host>:5432:*:<pg_user>:<pg_password>
            """,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # Could be added to override env
    # my_parser.add_argument(
    #     "malware-library",
    #     help="Path to a malware library",
    #     nargs="+",
    #     type=argparse.FileType("r"),
    # )

    my_parser.add_argument(
        "--chunksize",
        help="Chunksize in MiB for hashing the files in JWDs, defaults to 100 MiB",
        type=convert_arg_to_byte,
        default=100,
    )

    # not yet implemented
    #  my_parser.add_argument(
    #      "--remove-jobs",
    #      action="store_true",
    #      help="Removes the jobs from condor and fails them in Galaxy",
    #  )

    my_parser.add_argument(
        "--min-size",
        metavar="MIN_SIZE_MB",
        help="Minimum filesize im MB to limit the files to scan.",
        type=convert_arg_to_byte,
    )

    my_parser.add_argument(
        "--max-size",
        metavar="MAX_SIZE_MB",
        help="Maximum filesize im MB to limit the files to scan. \
            CAUTION: Not setting this value can lead to very long computation times",
        type=convert_arg_to_byte,
    )

    my_parser.add_argument(
        "--since",
        help="Access time in hours backwards from now",
        type=convert_arg_to_seconds,
    )

    my_parser.add_argument(
        "--tool",
        help="A string to filter tools in the tool_id column of currently running jobs. \
            Use like 'grep' after the gxadmin query queue-details command.",
        type=str,
        default="",
    )
    my_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Report not only the job and user ID that matched, but also Path of matched file and malware info. \
            If set, the scanning process will quit after the first match in a JWD to save resources.",
    )
    my_parser.add_argument(
        "-i",
        "--interactive",
        action="store_true",
        help="Show progress bar. Leave unset for cleaner logs and slightly higher performance",
    )

    return my_parser


class Job:
    def __init__(
        self,
        galaxy_id: int,
        object_store_id: int,
        user_id: int,
        user_name: str,
        tool_id: str,
        job_runner_name: str,
        jwd=None,
    ) -> None:
        self.galaxy_id = galaxy_id
        self.object_store_id = object_store_id
        self.jwd = jwd
        self.user_id = user_id
        self.user_name = user_name
        self.tool_id = tool_id
        self.job_runner_name = job_runner_name

    def report_id_and_user_name(self) -> str:
        return f"{self.galaxy_id} {self.user_name}"


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
    Can also hold a path to a matched file
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


def file_accessed_in_range(
    file_stat: os.stat_result, since: int, now=CURRENT_TIME
) -> bool:
    if since is not None:
        if now - since > file_stat.st_atime:
            return False
    return True


def file_in_size_range(
    file_stat: os.stat_result, min_size=None, max_size=None
) -> bool:
    if min_size is not None:
        if file_stat.st_size < min_size:
            return False
    if max_size is not None:
        if file_stat.st_size > max_size:
            return False
    return True


def all_files_in_dir(dir: pathlib.Path, args) -> [pathlib.Path]:
    """
    Gets all files of given directory and its subdirectories and
    appends file to a list of pathlib.Path objects, if atime
    and the filesize is within the specified range.
    """
    files = []
    for root, _, filenames in os.walk(dir):
        for filename in filenames:
            file = pathlib.Path(os.path.join(root, filename))
            file_stat = file.stat()
            if file_in_size_range(
                file_stat, args.min_size, args.max_size
            ) and file_accessed_in_range(file_stat, args.since):
                files.append(file)
    return files


def load_malware_lib_from_env(env=CHECKSUM_FILE_ENV) -> dict:
    if not os.environ.get(env):
        raise ValueError(env)
    malware_lib_path = os.environ.get(env).strip()
    with open(malware_lib_path, "r") as malware_yaml:
        malware_lib = yaml.safe_load(malware_yaml)
    return malware_lib


def digest_file_crc32(chunksize: int, path: pathlib.Path) -> int:
    crc32 = 0
    with open(path, "rb") as specimen:
        while chunk := specimen.read(chunksize):
            crc32 = zlib.crc32(chunk, crc32)
    return crc32


def digest_file_sha1(chunksize: int, path: pathlib.Path) -> str:
    sha1 = hashlib.sha1()
    with open(path, "rb") as specimen:
        while chunk := specimen.read(chunksize):
            sha1.update(chunk)
    return sha1.hexdigest()


def scan_file_for_malware(
    chunksize: int, file: pathlib.Path, lib: [Malware]
) -> [Malware]:
    """
    Returning a list of Malware, because
    it could potentially happen (even if it should not),
    that the same signature was added to the library more than once
    under different names or, extrem unlikely,
    a hash collision occurs.
    Args:
        chunksize: Chunksize in bytes
        file: pathlib.Path to the file to be checked
        lib: a list ob Malware objects with CRC32 and SHA-1 sums
    Returns:
        A list of Malware objects with matching CRC32 AND SHA-1 sums
    """
    matches = []
    crc32 = digest_file_crc32(chunksize, file)
    sha1 = None
    for malware in lib:
        if malware.crc32 == crc32:
            if sha1 is None:
                sha1 = digest_file_sha1(chunksize, file)
            if malware.sha1 == sha1:
                matches.append(malware)
    return matches


def report_matching_malware(
    job: Job, malware: Malware, path: pathlib.Path
) -> str:
    """
    Create log line depending on verbosity
    """
    return f"{datetime.datetime.now()} {job.user_name} {job.galaxy_id} \
{malware.malware_class} {malware.name} {malware.version} {path}"


def construct_malware_list(malware_yaml: dict) -> [Malware]:
    """
    creates a flat list of malware objects, that hold all info
    The nested structure in yaml is for better optical structuring
    """
    malware_list = []
    for malware_class in malware_yaml:
        for pkg in malware_yaml[malware_class]:
            for version in malware_yaml[malware_class][pkg]:
                malware_list.append(
                    Malware(
                        malware_class=malware_class,
                        name=pkg,
                        version=version,
                        severity=malware_yaml[malware_class][pkg][version][
                            "severity"
                        ],
                        description=malware_yaml[malware_class][pkg][version][
                            "description"
                        ],
                        crc32=malware_yaml[malware_class][pkg][version][
                            "checksums"
                        ]["crc32"],
                        sha1=malware_yaml[malware_class][pkg][version][
                            "checksums"
                        ]["sha1"],
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
                SELECT id, object_store_id, tool_id, user_id, user, job_runner_name
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
            user_name,
            job_runner_name,
        ) in running_jobs:
            running_jobs_list.append(
                Job(
                    galaxy_id=job_id,
                    object_store_id=object_store_id,
                    tool_id=tool_id,
                    user_id=user_id,
                    user_name=user_name,
                    job_runner_name=job_runner_name,
                )
            )
        return running_jobs_list


def main():
    """
    Miner Finder's main function. Shows a status bar while processing the jobs found in Galaxy
    """
    args = make_parser().parse_args()
    jwd_getter = JWDGetter()
    db = RunningJobDatabase()
    malware_library = construct_malware_list(load_malware_lib_from_env())
    jobs = db.get_running_jobs(args.tool)
    if args.interactive:
        if args.verbose:
            print(
                "TIMESTAMP GALAXY_USER JOB_ID \
MALWARE_CLASS MALWARE MALWARE_VERSION PATH"
            )
        else:
            print("GALAXY_USER JOB_ID")
    for job in tqdm(
        jobs,
        disable=(not args.interactive),
        desc="Processing jobs…",
        ascii=False,
        ncols=75,
    ):
        jwd_path = jwd_getter.get_jwd_path(job)
        if pathlib.Path(jwd_path).exists():
            job.jwd = pathlib.Path(jwd_path)
            for file in all_files_in_dir(job.jwd, args):
                matching_malware = scan_file_for_malware(
                    chunksize=args.chunksize, file=file, lib=malware_library
                )
                if len(matching_malware) > 0:
                    print("\n")
                    if args.verbose:
                        for malware in matching_malware:
                            print(
                                report_matching_malware(
                                    job=job,
                                    malware=malware,
                                    path=file,
                                )
                            )
                    else:
                        print(job.report_id_and_user_name())
                        break

        else:
            print(
                f"JWD for Job {job.galaxy_id} found but does not exist in FS",
                file=sys.stderr,
            )

    print("Complete.")


# ✅ get a list of Galaxy IDs of currently running interactive jobs
# for each job
# ✅ get a list of all files (recursively) smaller than 10MB in that JWD using change_to_jwd.py
#  for each file
# ✅ hash that file with crc32
# ✅ compare hash to given list of hashes provided and if it matches,
# ✅ also hash with md5 and if that matches
# - extract the condor_id from file
# - gxadmin mutate fail-job $job
# - gxadmin report job-info $job
# - condor rm $condor_id
# - gxadmin report job-info | grep Owner

# extended and when tested:
# implement auto block with bioblend

if __name__ == "__main__":
    main()
