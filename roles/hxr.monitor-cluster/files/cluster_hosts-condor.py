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
    "Cpus",
    "TotalMemory",
    "Memory",
    "TotalGPUs",
    "GPUs",
    "NumDynamicSlots",
    "TotalLoadAvg",
]


def parse_inventory(path):
    """Return the hostnames listed in an Ansible inventory."""
    inventory = InventoryManager(loader=DataLoader(), sources=[path])
    return [host.name for host in inventory.get_hosts()]


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
    return {
        ad["Machine"]: {k.lower(): v for k, v in ad.items()}
        for ad in json.loads(raw)
    }


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


def tag(value):
    """Escape a value for use as an InfluxDB tag."""
    return re.sub(r"[ ,=]", "_", str(value))


def influx_line(host, ad, jobs):
    """Build one InfluxDB line-protocol record for a host."""
    galaxy_group = ad.get("galaxygroup", "unknown") if ad else "unknown"
    tags = f"host={tag(host)},galaxygroup={tag(galaxy_group)}"
    fields = [f"in_condor={1 if ad else 0}i", f"running_jobs={jobs}i"]
    if ad:
        fields += [
            f'state="{ad["state"]}"',
            f'activity="{ad["activity"]}"',
            f'cpus_total={int(ad["detectedcpus"])}i',
            f'cpus_free={int(ad["cpus"])}i',
            f'memory_total_mb={int(ad["totalmemory"])}i',
            f'memory_free_mb={int(ad["memory"])}i',
            f'gpus_total={int(ad["totalgpus"])}i',
            f'gpus_free={int(ad["gpus"])}i',
            f'dynamic_slots={int(ad["numdynamicslots"])}i',
            f'load={float(ad["totalloadavg"])}',
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

    for host in hosts:
        print(influx_line(host, facts.get(host), jobs.get(host, 0)))


if __name__ == "__main__":
    main()
