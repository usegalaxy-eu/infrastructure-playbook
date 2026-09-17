#!/usr/bin/env python3
"""One InfluxDB line per VGCN inventory host, with its HTCondor state."""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter

from ansible.inventory.manager import InventoryManager
from ansible.parsing.dataloader import DataLoader

DEFAULT_INVENTORY = "/etc/condor-monitored-hosts"
DEFAULT_SCHEDD = "sn09.galaxyproject.eu"

MACHINE_ATTRS = [
    "Machine",
    "State",
    "Activity",
    "GalaxyGroup",
    "DetectedCpus",
    "TotalMemory",
    "TotalGpus",
]

NORMAL_STATES = {"Unclaimed", "Claimed"}


def parse_inventory(path):
    """Parse an Ansible inventory into {hostname: group}."""
    inventory = InventoryManager(loader=DataLoader(), sources=[path])
    hosts = {}
    for name, group in inventory.groups.items():
        if name in ("all", "ungrouped"):
            continue
        for host in group.get_hosts():
            hosts[host.name] = name
    return hosts


def run(cmd):
    """Run a command and return its stdout, or exit with a message."""
    try:
        out = subprocess.run(cmd, check=True, capture_output=True)
    except Exception as err:
        print(f"error running {cmd[0]}: {err}", file=sys.stderr)
        sys.exit(1)
    return out.stdout.decode()


def machine_facts():
    """Return {machine: classad} for every partitionable slot."""
    raw = run(
        [
            "condor_status",
            "-json",
            "-attributes",
            ",".join(MACHINE_ATTRS),
            "-constraint",
            'SlotType == "Partitionable"',
        ]
    ).strip()
    if not raw:
        return {}
    return {ad["Machine"]: ad for ad in json.loads(raw)}


def job_counts(schedd):
    """Return {machine: running job count} from the job queue."""
    raw = run(
        [
            "condor_q",
            "-name",
            schedd,
            "-constraint",
            "JobStatus == 2",
            "-af",
            'split(RemoteHost, "@")[1]',
        ]
    )
    names = (n.strip() for n in raw.splitlines())
    return Counter(n for n in names if n and n != "undefined")


def host_status(ad, jobs):
    """Describe what the machine is actually doing."""
    if ad is None:
        return "absent"
    state = ad.get("State", "unknown")
    if state not in NORMAL_STATES:
        return state.lower()
    return "busy" if jobs > 0 else "idle"


def tag(value):
    """Escape a value for use as an InfluxDB tag."""
    return re.sub(r"[ ,=]", "_", str(value))


def influx_line(host, group, ad, jobs):
    """Build one InfluxDB line-protocol record for a host."""
    galaxy_group = ad.get("GalaxyGroup", "unknown") if ad else "unknown"
    tags = ",".join(
        [
            f"host={tag(host)}",
            f"inventory_group={tag(group)}",
            f"galaxygroup={tag(galaxy_group)}",
        ]
    )
    fields = [
        f"in_condor={1 if ad else 0}i",
        f"running_jobs={jobs}i",
        f'status="{host_status(ad, jobs)}"',
    ]
    if ad:
        fields += [
            f'state="{ad["State"]}"',
            f'activity="{ad["Activity"]}"',
            f'cpus={int(ad["DetectedCpus"])}i',
            f'memory_mb={int(ad["TotalMemory"])}i',
            f'gpus={int(ad["TotalGpus"])}i',
        ]
    return f"htcondor_host_status,{tags} " + ",".join(fields)


def main():
    """Print one line per inventory host."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        default=DEFAULT_INVENTORY,
        help="Ansible inventory listing the expected hosts",
    )
    parser.add_argument(
        "--schedd",
        default=DEFAULT_SCHEDD,
        help="schedd to read the job queue from",
    )
    args = parser.parse_args()

    try:
        hosts = parse_inventory(args.inventory)
    except Exception as err:
        print(f"cannot read inventory {args.inventory}: {err}", file=sys.stderr)
        sys.exit(1)

    facts = machine_facts()
    jobs = job_counts(args.schedd)

    for host, group in hosts.items():
        print(influx_line(host, group, facts.get(host), jobs.get(host, 0)))


if __name__ == "__main__":
    main()
