#!/usr/bin/env python
# ===============================================================================
# Copyright (c) 2016 by Frank Fischer
# ===============================================================================
from __future__ import unicode_literals, print_function, with_statement

import os
import pickle
import re
import time


def get_times():
    """
    Retrieve wall time from cloud-init meta-data.

    Cloud-Init saves all passed meta-data into a cloudinit.sources.DataSource object with attribute 'metadata'
    A DataSourceOpenStack object stores information on additional metadata in a sub-dictionary 'meta'."""
    try:
        with open("/var/lib/cloud/instance/obj.pkl", "r") as file_:
            data = pickle.load(file_)
    except IOError:
        return

    meta = data.metadata.get("meta")
    if meta is None:
        raise EnvironmentError("Wrong virtualization environment.")

    keys = [x for x in meta.keys() if re.search(".*Wall.*Time", x, re.IGNORECASE)]
    if len(keys) != 1:
        if len(keys) == 0:
            raise ValueError("No meta-data entry with key 'WallTime'")
        else:
            raise ValueError("Ambiguous meta-data found: %s" % keys)

    walltime = int(meta.get(keys[0]))
    starttime = int(os.stat("/var/lib/cloud/instance/obj.pkl").st_ctime)
    return walltime, starttime


def save_env(wall_time_=None, start_time_=None, environment_file="/etc/environment"):
    """
    Save wall-time information to system variables WALLTIME & BOOTTIME.

    Values by default are stored in /etc/environment, discarding old wall-/boottime entries, preserving the rest.
    """
    if not os.access(environment_file, os.W_OK):
        raise EnvironmentError("Can't write to %s" % environment_file)

    with open(name=environment_file, mode="r") as file_:
        # keep results != WALLTIME/BOOTTIME
        content = [entry for entry in file_.readlines() if re.match("(?:WALL|BOOT)TIME", entry, re.IGNORECASE) is None]
        if wall_time_ is not None:
            content.append("WALLTIME=%d\n" % wall_time_)
        if start_time_ is not None:
            content.append("BOOTTIME=%d\n" % start_time_)
    with open(name=environment_file, mode="w") as file_:
        file_.writelines(content)


if __name__ == "__main__":
    try:
        wall_time, start_time = get_times()
        # Condor parses stdout as configuration file content
        print("MachineMaxWalltime=%d" % wall_time)
        print("MachineStarttime=%d" % start_time)
        save_env(wall_time, start_time)
    except (ValueError, EnvironmentError, TypeError):
        # Fall back on reading /proc/uptime
        with open("/proc/uptime", "r") as _file:
            uptime = float(_file.readline().split()[0])
        boot_time = int(time.time() - uptime)
        print("MachineStarttime=%d" % boot_time)

