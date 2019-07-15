#!/usr/bin/env python
import yaml
import os
import sys

D = os.path.dirname(os.path.realpath(os.path.join(__file__, "..")))

jcaas_conf = yaml.load(
    open(
        os.path.join(D, "files/galaxy/dynamic_rules/usegalaxy/tool_destinations.yaml"),
        "r",
    )
)
jcaas_conf2 = {}
for (k, v) in jcaas_conf.items():
    jcaas_conf2[k.lower()] = v


def get_tool_id(tool_id):
    if tool_id.count("/") == 0:
        return tool_id

    if tool_id.count("/") == 5:
        (server, _, owner, repo, name, version) = tool_id.split("/")
        return name

    return tool_id


max_mem = 0
max_cpu = 0


for v in sys.stdin.read().split("\n"):
    tool_id = get_tool_id(v).lower().strip()

    if tool_id in jcaas_conf2:
        tool_conf = jcaas_conf2[tool_id]
        print(tool_id, tool_conf)

        if tool_conf.get("mem", 4) > max_mem:
            max_mem = tool_conf.get("mem", 4)

        if tool_conf.get("cores", 4) > max_cpu:
            max_cpu = tool_conf.get("cores", 4)

print("Maximums: memory=%s cpu=%s" % (max_mem, max_cpu))
