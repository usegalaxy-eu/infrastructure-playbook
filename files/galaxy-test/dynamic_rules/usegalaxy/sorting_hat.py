#!/usr/bin/env python
# usegalaxy.eu sorting hat
from galaxy.jobs import JobDestination
from galaxy.jobs.mapper import JobMappingException

import copy
import math
import os
import yaml

# The default / base specification for the different environments.
SPECIFICATION_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'destination_specifications.yaml')
with open(SPECIFICATION_PATH, 'r') as handle:
    SPECIFICATIONS = yaml.load(handle)

TOOL_DESTINATION_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tool_destinations.yaml')
with open(TOOL_DESTINATION_PATH, 'r') as handle:
    TOOL_DESTINATIONS = yaml.load(handle)


def assert_permissions(tool_spec, user_email, user_roles):
    """
    Permissions testing.

    - default state is to allow everyone to run everything.
    - If there is a permissions block, `deny: all` is the default.
    - We ONLY support allowing specific users to run something. This DOES NOT
      support preventing specific users from running something.

    """
    exception_text = "This tool is temporarily disabled due to internal policy. Please contact us if you have issues."
    # If there is no permissions block then it's going to be fine for everyone.
    if 'permissions' not in tool_spec:
        return

    permissions = tool_spec['permissions']

    # TODO(hxr): write a custom tool thing linter.
    # We'll be extra defensive here since I don't think I trust us to get
    # linting right for now.
    if len(permissions.keys()) == 0:
        raise Exception("JCaaS Configuration error 1")

    # And for typos.
    if 'allow' not in permissions:
        raise Exception("JCaaS Configuration error 2")

    if 'users' not in permissions['allow'] and 'roles' not in permissions['allow']:
        raise Exception("JCaaS Configuration error 3")
    # ENDTODO

    # Pull out allowed users and roles, defaulting to empty lists if the keys
    # aren't there.
    allowed_users = permissions['allow'].get('users', [])
    allowed_roles = permissions['allow'].get('roles', [])

    # If the user is on our list, yay, return.
    if user_email in allowed_users:
        return

    # If one of their roles is in our list
    if any([user_role in allowed_roles for user_role in user_roles]):
        return

    # Auth failure.
    raise Exception(exception_text)


def get_tool_id(tool_id):
    """
    Convert ``toolshed.g2.bx.psu.edu/repos/devteam/column_maker/Add_a_column1/1.1.0``
    to ``Add_a_column``

    :param str tool_id: a tool id, can be the short kind (e.g. upload1) or the long kind with the full TS path.

    :returns: a short tool ID.
    :rtype: str
    """
    if tool_id.count('/') == 0:
        # E.g. upload1, etc.
        return tool_id

    # what about odd ones.
    if tool_id.count('/') == 5:
        (server, _, owner, repo, name, version) = tool_id.split('/')
        return name

    return tool_id


def name_it(tool_spec):
    if 'cores' in tool_spec:
        name = '%scores_%sG' % (tool_spec.get('cores', 1), tool_spec.get('mem', 4))
    elif len(tool_spec.keys()) == 0 or (len(tool_spec.keys()) == 1 and 'runner' in tool_spec):
        name = '%s_default' % tool_spec.get('runner', 'condor')
    else:
        name = '%sG_memory' % tool_spec.get('mem', 4)

    if tool_spec.get('tmp', None) == 'large':
        name += '_large'

    if 'name' in tool_spec:
        name += '_' + tool_spec['name']

    return name


def _get_limits(destination, default_cores=1, default_mem=4, default_gpus=0):
    limits = {'cores': default_cores, 'mem': default_mem, 'gpus': default_gpus}
    limits.update(SPECIFICATIONS.get(destination).get('limits', {}))
    return limits


def build_spec(tool_spec, runner_hint=None):
    destination = tool_spec.get('runner', 'condor')

    # TODO: REMOVE. Temporary hack, should be safe to remove now
    if runner_hint is not None:
        destination = runner_hint

    env = dict(SPECIFICATIONS.get(destination, {'env': {}})['env'])
    params = dict(SPECIFICATIONS.get(destination, {'params': {}})['params'])
    # A dictionary that stores the "raw" details that went into the template.
    raw_allocation_details = {}

    # We define the default memory and cores for all jobs. This is
    # semi-internal, and may not be properly propagated to the end tool
    tool_memory = tool_spec.get('mem', 4)
    tool_cores = tool_spec.get('cores', 1)
    tool_gpus = tool_spec.get('gpus', 0)

    # We apply some constraints to these values, to ensure that we do not
    # produce unschedulable jobs, requesting more ram/cpu than is available in a
    # given location. Currently we clamp those values rather than intelligently
    # re-scheduling to a different location due to TaaS constraints.
    limits = _get_limits(destination)
    if 'condor' in destination:
        tool_memory = min(tool_memory, limits.get('mem'))
        tool_cores = min(tool_cores, limits.get('cores'))

    if 'remote_cluster_mq' in destination:
        tool_memory = min(tool_memory, limits.get('mem'))
        tool_cores = min(tool_cores, limits.get('cores'))
        tool_gpus = min(tool_gpus, limits.get('gpus'))

    kwargs = {
        # Higher numbers are lower priority, like `nice`.
        'PRIORITY': tool_spec.get('priority', 128),
        'MEMORY': str(tool_memory) + 'G',
        'PARALLELISATION': "",
        'NATIVE_SPEC_EXTRA': "",
        'GPUS': "",
    }
    # Allow more human-friendly specification
    if 'nativeSpecification' in params:
        params['nativeSpecification'] = params['nativeSpecification'].replace('\n', ' ').strip()

    # We have some destination specific kwargs. `nativeSpecExtra` and `tmp` are only defined for SGE
    if 'condor' in destination:
        if 'cores' in tool_spec:
            kwargs['PARALLELISATION'] = tool_cores
            raw_allocation_details['cpu'] = tool_cores
        else:
            del params['request_cpus']

        if 'mem' in tool_spec:
            raw_allocation_details['mem'] = tool_memory

        if 'requirements' in tool_spec:
            params['requirements'] = tool_spec['requirements']

        if 'rank' in tool_spec:
            params['rank'] = tool_spec['rank']

    if 'remote_cluster_mq' in destination:
        if 'cores' in tool_spec:
            kwargs['PARALLELISATION'] = tool_cores
        else:
            del params['submit_submit_request_cpus']

        if 'gpus' in tool_spec and tool_gpus > 0:
            kwargs['GPUS'] = tool_gpus

    # Update env and params from kwargs.
    env.update(tool_spec.get('env', {}))
    env = {k: str(v).format(**kwargs) for (k, v) in env.items()}
    params.update(tool_spec.get('params', {}))
    params = {k: str(v).format(**kwargs) for (k, v) in params.items()}

    if destination == 'sge':
        runner = 'drmaa'
    elif 'condor' in destination:
        runner = 'condor'
    elif 'remote_cluster_mq' in destination:
        runner = destination.replace('remote_cluster_mq', 'pulsar_eu')
    else:
        runner = 'local'

    env = [dict(name=k, value=v) for (k, v) in env.items()]
    return env, params, runner, raw_allocation_details


def reroute_to_dedicated(tool_spec, user_roles):
    """
    Re-route users to correct destinations. Some users will be part of a role
    with dedicated training resources.
    """
    # Collect their possible training roles identifiers.
    training_roles = [role for role in user_roles if role.startswith('training-')]
    if any([role.startswith('training-gcc-') for role in training_roles]):
        training_roles.append('training-gcc')

    # No changes to specification.
    if len(training_roles) == 0:
        # Require that the jobs do not run on these dedicated training machines.
        return {'requirements': 'GalaxyGroup == "compute"'}

    # Otherwise, the user does have one or more training roles.
    # So we must construct a requirement / ranking expression.
    training_expr = " || ".join(['(GalaxyGroup == "%s")' % role for role in training_roles])
    return {
        # We require that it does not run on machines that the user is not in the role for.
        'requirements': '(GalaxyGroup == "compute") || (%s)' % training_expr,
        # We then rank based on what they *do* have the roles for
        'rank': training_expr,
    }


def _finalize_tool_spec(tool_id, user_roles, memory_scale=1.0):
    # Find the 'short' tool ID which is what is used in the .yaml file.
    tool = get_tool_id(tool_id)
    # Pull the tool specification (i.e. job destination configuration for this tool)
    tool_spec = copy.deepcopy(TOOL_DESTINATIONS.get(tool, {}))
    # Update the tool specification with any training resources that are available
    tool_spec.update(reroute_to_dedicated(tool_spec, user_roles))

    tool_spec['mem'] = tool_spec.get('mem', 4) * memory_scale

    # Only two tools are truly special.
    if tool_id in ('upload1', '__DATA_FETCH__'):
        tool_spec = {
            'mem': 0.3,
            'runner': 'condor',
            'rank': 'GalaxyGroup == "upload"',
            'requirements': 'GalaxyTraining == false',
            'env': {
                'TEMP': '/data/1/galaxy_db/tmp/'
            }
        }
    elif tool_id == '__SET_METADATA__':
        tool_spec = {
            'mem': 0.3,
            'runner': 'condor',
            'rank': 'GalaxyGroup == "metadata"',
            'requirements': 'GalaxyTraining == false',
        }
    # These we're running on a specific subset
    elif 'interactive_tool_' in tool_id:
        tool_spec['requirements'] = 'GalaxyCluster == "backofen"'

    return tool_spec


def convert_to(tool_spec, runner):
    tool_spec['runner'] = runner

    if runner == 'sge':
        # sge doesn't accept non-ints
        tool_spec['mem'] = int(math.ceil(tool_spec['mem']))

    return tool_spec


def _gateway(tool_id, user_roles, user_id, user_email, memory_scale=1.0):
    tool_spec = _finalize_tool_spec(tool_id, user_roles, memory_scale=memory_scale)

    # Now build the full spec
    runner_hint = None

    if tool_id != 'upload1':
        hints = [x for x in user_roles if x.startswith('destination-')]
        if len(hints) > 0:
            runner_hint = hints[0].replace('destination-pulsar-', 'remote_cluster_mq_')

    # Ensure that this tool is permitted to run, otherwise, throw an exception.
    assert_permissions(tool_spec, user_email, user_roles)

    env, params, runner, _ = build_spec(tool_spec, runner_hint=runner_hint)
    params['accounting_group_user'] = str(user_id)
    params['description'] = get_tool_id(tool_id)

    return env, params, runner, tool_spec


def gateway(tool_id, user, memory_scale=1.0, next_dest=None):
    # And run it.
    if user:
        user_roles = [role.name for role in user.all_roles() if not role.deleted]
        email = user.email
        user_id = user.id
    else:
        user_roles = []
        email = ''
        user_id = -1

    try:
        env, params, runner, spec = _gateway(tool_id, user_roles, user_id, email, memory_scale=memory_scale)
    except Exception as e:
        return JobMappingException(str(e))

    resubmit = []
    if next_dest:
        resubmit = [{
            'condition': 'any_failure and attempt <= 3',
            'destination': next_dest
        }]

    name = name_it(spec)
    return JobDestination(
        id=name,
        runner=runner,
        params=params,
        env=env,
        resubmit=resubmit,
    )

def gateway_1x(tool_id, user):
    return gateway(tool_id, user, memory_scale=1, next_dest='gateway_1_5x')

def gateway_1_5x(tool_id, user):
    return gateway(tool_id, user, memory_scale=1.5, next_dest='gateway_2x')

def gateway_2x(tool_id, user):
    return gateway(tool_id, user, memory_scale=2)
