#!/usr/bin/env python
import json
import sys


def get_tool_id(tool_id):
    if tool_id.count("/") == 0:
        return tool_id

    if tool_id.count("/") == 5:
        (server, _, owner, repo, name, version) = tool_id.split("/")
        return name

    return tool_id


def tools_from_wf(data):

    for k, v in data["steps"].items():
        if v["tool_id"] is None:
            continue

        if "subworkflow" in v:
            yield from tools_from_wf(v["subworkflow"])
        else:
            yield get_tool_id(v["tool_id"])


def obtain():
    for f in sys.argv[1:]:
        with open(f, "r") as handle:
            data = json.load(handle)
        yield from tools_from_wf(data)


for x in obtain():
    print(x)
