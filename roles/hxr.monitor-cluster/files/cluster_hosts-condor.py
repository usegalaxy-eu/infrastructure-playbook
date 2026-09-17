#!/usr/bin/env python3
"""One InfluxDB line per VGCN inventory host, with its HTCondor state."""

import os
import re
import subprocess
import sys

INVENTORY = os.environ.get(
    "CONDOR_HOSTS_INVENTORY", "/etc/condor-monitored-hosts"
)


def parse_inventory(path):
    """Parse an Ansible INI inventory into {hostname: group}."""
    hosts, group = {}, None
    with open(path) as f:
        for line in f:
            line = line.split("#")[0].strip()
            if not line:
                continue
            m = re.match(r"^\[([^\]]+)\]$", line)
            if m:
                group = m.group(1)
                continue
            if group:
                hosts[line.split()[0]] = group
    return hosts


def parse_machines(rows):
    """Turn partitionable-slot rows into {machine: facts}."""
    facts = {}
    for row in rows:
        f = row.split()
        if len(f) < 6:
            continue
        facts[f[0]] = {
            "state": f[1],
            "activity": f[2],
            "galaxygroup": f[3],
            "cpus": f[4],
            "memory_mb": f[5],
            "gpus": f[6] if len(f) > 6 else "0",
        }
    return facts


def parse_jobs(rows):
    """Count busy slots per machine."""
    counts = {}
    for row in rows:
        name = row.strip()
        if name:
            counts[name] = counts.get(name, 0) + 1
    return counts


def condor(args):
    """Run condor_status and return its output lines."""
    try:
        out = subprocess.run(
            ["condor_status"] + args, check=True, capture_output=True
        )
    except Exception as err:
        print(f"error running condor_status: {err}", file=sys.stderr)
        sys.exit(1)
    return out.stdout.decode().splitlines()


def tag(value):
    """Influx tag values can't contain spaces, commas or equals signs."""
    return re.sub(r"[ ,=]", "_", str(value))


def influx_line(host, group, facts, jobs):
    """Build one InfluxDB line-protocol record for a host."""
    present = facts is not None
    if not present:
        status = "absent"
    elif jobs > 0:
        status = "busy"
    else:
        status = "idle"
    gg = facts["galaxygroup"] if present else "unknown"
    if gg == "undefined":
        gg = "unknown"
    tags = (
        f"host={tag(host)},inventory_group={tag(group)},galaxygroup={tag(gg)}"
    )
    fields = [
        f"in_condor={1 if present else 0}i",
        f"running_jobs={jobs}i",
        f'status="{status}"',
    ]
    if present:
        fields += [
            f'state="{facts["state"]}"',
            f'activity="{facts["activity"]}"',
            f'cpus={facts["cpus"]}i',
            f'memory_mb={facts["memory_mb"]}i',
            f'gpus={facts["gpus"]}i',
        ]
    return f"htcondor_host_status,{tags} " + ",".join(fields)


def main():
    """Print one line per inventory host."""
    if not os.path.exists(INVENTORY):
        print(f"inventory file not found: {INVENTORY}", file=sys.stderr)
        sys.exit(1)
    hosts = parse_inventory(INVENTORY)
    facts = parse_machines(
        condor(
            [
                "-autoformat",
                "Machine",
                "State",
                "Activity",
                "GalaxyGroup",
                "DetectedCpus",
                "TotalMemory",
                "TotalGpus",
                "-constraint",
                'SlotType == "Partitionable"',
            ]
        )
    )
    jobs = parse_jobs(
        condor(
            [
                "-autoformat",
                "Machine",
                "-constraint",
                'State == "Claimed" && Activity == "Busy"',
            ]
        )
    )

    for host, group in hosts.items():
        print(influx_line(host, group, facts.get(host), jobs.get(host, 0)))


if __name__ == "__main__":
    main()
