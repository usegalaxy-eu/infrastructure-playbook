#!/usr/bin/env python
# A command line script that iterates over the currently running jobs and stops them as well as logs the user,
# when a file in the JWD matches to a list of hashes

import galaxy_jwd
import argparse
import pathlib
import tqdm


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
        type=argparse.FileType("r")
    )

    my_parser.add_argument(
        "sha1",
        help="Path to a SHA1 checksum file (optional for more precision)",
        nargs="+",
        type=argparse.FileType("r")
        required=False,
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
        type=argparse.FileType("r")
    )

    my_parser.add_argument(
        "--min-size",
        help="Minimum filesize im MB to limit the files to scan.",
        type=int
    )

    my_parser.add_argument(
        "--max-size",
        help="Maximum filesize im MB to limit the files to scan. \
            CAUTION: Not setting this value can lead to very long computation times",
        type=int
    )

    my_parser.add_argument(
        "--since",
        help="Access time in hours backwards from now",
        type=int
    )

    my_parser.add_argument(
        "--queue-keyword",
        help="A string to search for in the rows of currently running jobs. \
            Use like 'grep' after the gxadmin query queue-details command.",
        type=str,
    )
    return my_parser

def main():
    """
    Miner Finder's main function. Shows a status bar while processing the jobs found in Galaxy
    """
for i in tqdm (range (jobs), 
               desc="Processing jobs…", 
               ascii=False, ncols=75):
    time.sleep(0.01)
     
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
