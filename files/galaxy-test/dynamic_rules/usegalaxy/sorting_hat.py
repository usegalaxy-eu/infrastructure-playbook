#!/usr/bin/env python
# usegalaxy.eu sorting hat
"""

                                   .'lddc,.
                                'cxOOOOOOOOOxoc;,...
                            .:dOOOOOOOOOOOOOOOOOOOOOOOl
                        .;dOOOOOOOOOOOOOOxcdOOOOOOOkl.
                       oOOOOOOOOOOOOOOOx,    ......
                     .xOOkkkOOOOOOOOOk'
                    .xOOkkkOOOOOOOOO00.
                    dOOkkkOOOOOOOOOOOOd
                   cOOkkkOOOOOOOOOOOOOO'
                  .OOOkkOOOOOOOOOOOOOOOd
                  dOOkkOOOOOOOOOOOOOOOOO,
                 .OOOOOOOOOOOOOOOOOOOOOOx
                 cOOOOOOOOOOOOOOOOOOOOOOO;
                 kOOOOOOOxddddddddxOOOOOOk.
        ..,:cldxdlodxxkkO;'''''''';Okkxxdookxdlc:,..
   .;lxO00000000d;;;;;;;;,'';;;;'',;;;;;;;:k00000000Oxl;.
  d0000000000000xl::;;;;;,'''''''',;;;;;::lk0000000000000d
 .d00000000000000000OkxxxdoooooooodxxxkO00000000000000000d.
   .;lxO00000000000000000000000000000000000000000000Oxl;.
        ..,;cloxkOO0000000000000000000000OOkxdlc;,..
                     ..................

"Oh, you may not think I'm pretty,
But don't judge on what you see,"

"For I'm the [Galaxy] Sorting Hat
And I can cap them all."

You might belong in Condor,
Where dwell the slow to compute,

You might belong in Pulsar,
Far flung and remote,

Or yet in wise old Singularity,
If you're evil and insecure

--hexylena
"""
import copy
import os
import yaml

from galaxy.jobs import JobDestination
from galaxy.jobs.mapper import JobMappingException
from random import sample


class DetailsFromYamlFile:
    """
    Retrieve details from a yaml file
    """
    def __init__(self, yaml_file):
        yaml_file_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), yaml_file)
        if os.path.isfile(yaml_file_path):
            with open(yaml_file_path, 'r') as handle:
                self._conf = yaml.load(handle, Loader=yaml.SafeLoader)

    @property
    def conf(self):
        return self._conf

    def get(self, first_level_label, second_level_label=None):
        for key, value in self._conf.items():
            if key == first_level_label:
                if second_level_label is None:
                    return value
                else:
                    return value.get(second_level_label)
        return None

    def get_path(self, label):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), self.get('file_paths', label))



# Sorting Hat configuration details are defined in this file
SH_CONFIGURATION_FILENAME = 'sorting_hat.yaml'

sh_conf = DetailsFromYamlFile(SH_CONFIGURATION_FILENAME)
DEFAULT_DESTINATION = sh_conf.get('default_destination')
DEFAULT_TOOL_SPEC = sh_conf.get('default_tool_specification')
FAST_TURNAROUND = sh_conf.get('fast_turnaround')
FDID_PREFIX = sh_conf.get('force_destination_id_prefix')
SPECIAL_TOOLS = sh_conf.get('special_tools')


# The default / base specification for the different environments.
SPECIFICATION_PATH = sh_conf.get_path('destination_specifications')
SPECIFICATIONS = DetailsFromYamlFile(SPECIFICATION_PATH).conf

TOOL_DESTINATION_PATH = sh_conf.get_path('tool_destinations')
TOOL_DESTINATIONS = DetailsFromYamlFile(TOOL_DESTINATION_PATH).conf

JOINT_DESTINATIONS_PATH = sh_conf.get_path('joint_destinations')
JOINT_DESTINATIONS = DetailsFromYamlFile(JOINT_DESTINATIONS_PATH).conf


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


def name_it(tool_spec, prefix=FDID_PREFIX):
    """
    Create a destination's name using the tool's specification.
    Can be also forced to return a specific string
    """
    if 'cores' in tool_spec:
        name = '%scores_%sG' % (tool_spec.get('cores', 1), tool_spec.get('mem', 4))
    elif len(tool_spec.keys()) == 0 or (len(tool_spec.keys()) == 1 and 'runner' in tool_spec):
        name = '%s_default' % tool_spec.get('runner')
    else:
        name = '%sG_memory' % tool_spec.get('mem', 4)

    if tool_spec.get('tmp', None) == 'large':
        name += '_large'

    if 'name' in tool_spec:
        name += '_' + tool_spec['name']

    # Force a replacement of the destination's id
    if tool_spec.get('force_destination_id', False):
        name = prefix + tool_spec.get('runner')

    return name


def _get_limits(destination, dest_spec=SPECIFICATIONS, default_cores=1, default_mem=4, default_gpus=0):
    """
    Get destination's limits
    """
    limits = {'cores': default_cores, 'mem': default_mem, 'gpus': default_gpus}
    limits.update(dest_spec.get(destination).get('limits', {}))
    return limits


def _weighted_random_sampling(destinations, dest_spec=SPECIFICATIONS):
    bunch = []
    for d in destinations:
        weight = dest_spec[d].get('nodes', 1)
        bunch += [d]*weight
    destination = sample(bunch, 1)[0]
    return destination


def build_spec(tool_spec, dest_spec=SPECIFICATIONS, runner_hint=None):
    destination = runner_hint if runner_hint else tool_spec.get('runner')

    if destination not in dest_spec:
        if destination in JOINT_DESTINATIONS:
            destination = _weighted_random_sampling(JOINT_DESTINATIONS[destination])
        else:
            destination = DEFAULT_DESTINATION

    env = dict(dest_spec.get(destination, {'env': {}})['env'])
    params = dict(dest_spec.get(destination, {'params': {}})['params'])
    tags = {dest_spec.get(destination).get('tags', None)}

    # We define the default memory and cores for all jobs.
    tool_memory = tool_spec.get('mem')
    tool_cores = tool_spec.get('cores')
    tool_gpus = tool_spec.get('gpus')

    # We apply some constraints to these values, to ensure that we do not
    # produce unschedulable jobs, requesting more ram/cpu than is available in a
    # given location. Currently we clamp those values rather than intelligently
    # re-scheduling to a different location due to TaaS constraints.
    limits = _get_limits(destination, dest_spec=dest_spec)
    tool_memory = min(tool_memory, limits.get('mem'))
    tool_cores = min(tool_cores, limits.get('cores'))
    tool_gpus = min(tool_gpus, limits.get('gpus'))

    kwargs = {
        # Higher numbers are lower priority, like `nice`.
        'PRIORITY': tool_spec.get('priority', 128),
        'MEMORY': str(tool_memory) + 'G',
        'MEMORY_MB': int(tool_memory * 1024),
        'PARALLELISATION': tool_cores,
        'NATIVE_SPEC_EXTRA': "",
        'GPUS': tool_gpus,
    }

    if 'docker_enabled' in params and params['docker_enabled']:
        for k in tool_spec:
            if k.startswith('docker'):
                params[k] = tool_spec.get(k, '')

    if 'condor' in destination:
        if 'requirements' in tool_spec:
            params['requirements'] = tool_spec['requirements']

        if 'rank' in tool_spec:
            params['rank'] = tool_spec['rank']

        if '+Group' in tool_spec:
            params['+Group'] = tool_spec['+Group']

    if 'remote_cluster_mq' in destination:
        # specific for condor cluster
        if tool_gpus == 0 and 'submit_request_gpus' in params:
            del params['submit_request_gpus']

    # Update env and params from kwargs.
    env.update(tool_spec.get('env', {}))
    env = {k: str(v).format(**kwargs) for (k, v) in env.items()}

    params.update(tool_spec.get('params', {}))
    for (k, v) in params.items():
        if not isinstance(v, list):
            params[k] = str(v).format(**kwargs)
        else:
            params[k] = v

    tags.add(tool_spec.get('tags', None))
    tags.discard(None)
    tags = ','.join([x for x in tags if x is not None]) if len(tags) > 0 else None

    if 'condor' in destination:
        runner = 'condor'
    elif 'remote_cluster_mq' in destination:
        # destination label has to follow this convention:
        # remote_cluster_mq_feature1_feature2_feature3_pulsarid
        runner = "_".join(['pulsar_eu', destination.split('_').pop()])
    else:
        runner = 'local'

    env = [dict(name=k, value=v) for (k, v) in env.items()]
    return env, params, runner, tags


def reroute_to_dedicated(user_roles):
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
    training_labels = '"'+", ".join(['%s' % role for role in training_roles])+'"'
    return {
        # We require that it does not run on machines that the user is not in the role for.
        'requirements': '(GalaxyGroup == "compute") || (%s)' % training_expr,
        # We then rank based on what they *do* have the roles for
        '+Group': training_labels,
    }


def _finalize_tool_spec(tool_id, user_roles, special_tools=SPECIAL_TOOLS, tools_spec=TOOL_DESTINATIONS, memory_scale=1.0):
    # Find the 'short' tool ID which is what is used in the .yaml file.
    tool = get_tool_id(tool_id)
    # Pull the tool specification (i.e. job destination configuration for this tool)
    tool_spec = copy.deepcopy(tools_spec.get(tool, {}))
    # Update the tool specification with any training resources that are available
    tool_spec.update(reroute_to_dedicated(user_roles))

    # Update the tool specification with default values if they are not present
    for s in DEFAULT_TOOL_SPEC:
        tool_spec[s] = tool_spec.get(s, DEFAULT_TOOL_SPEC[s])

    tool_spec['mem'] *= memory_scale

    # Only few tools are truly special.
    if tool_id in special_tools.get('upload'):
        tool_spec = {
            'cores': 1,
            'mem': 0.3,
            'gpus': 0,
            'runner': 'condor_upload',
            'rank': 'GalaxyGroup == "upload"',
            'requirements': 'GalaxyTraining == false',
            'env': {
                'TEMP': '/data/1/galaxy_db/tmp/'
            }
        }
    elif tool_id in special_tools.get('metadata'):
        tool_spec = {
            'cores': 1,
            'mem': 0.3,
            'gpus': 0,
            'runner': 'condor_upload',
            'rank': 'GalaxyGroup == "metadata"',
            'requirements': 'GalaxyTraining == false',
        }
    # These we're running on a specific nodes subset
    elif 'interactive_tool_' in tool_id:
        tool_spec['requirements'] = 'GalaxyDockerHack == True && GalaxyGroup == "compute"'

    return tool_spec


def _gateway(tool_id, user_preferences, user_roles, user_id, user_email, ft=FAST_TURNAROUND,
             special_tools=SPECIAL_TOOLS, memory_scale=1.0):
    tool_spec = _finalize_tool_spec(tool_id, user_roles, memory_scale=memory_scale)

    # Now build the full spec

    # Use this hint to force a destination (e.g. defined from the user's preferences)
    runner_hint = None
    if tool_id not in special_tools.get('upload') or tool_id not in special_tools.get('metadata'):
        for data_item in user_preferences:
            if "distributed_compute|remote_resources" in data_item:
                if user_preferences[data_item] != "None":
                    runner_hint = user_preferences[data_item]

    # Ensure that this tool is permitted to run, otherwise, throw an exception.
    assert_permissions(tool_spec, user_email, user_roles)

    env, params, runner, tags = build_spec(tool_spec, runner_hint=runner_hint)
    params['accounting_group_user'] = str(user_id)
    params['description'] = get_tool_id(tool_id)

    # This is a special case, we're requiring it for faster feedback / turnaround times.
    # Fast turnaround can be enabled for all the jobs or per single user adding a user role
    # with the label described by 'role_label' key.
    ft_enabled = ft.get('enabled')
    ft_mode = ft.get('mode')
    ft_role_label = ft.get('role_label')
    ft_requirements = ft.get('requirements')

    if ft_enabled:
        if (ft_mode == 'user_roles' and ft_role_label in user_roles) or ft_mode == 'all_jobs':
            params['requirements'] = ft_requirements

    return env, params, runner, tool_spec, tags


def gateway(tool_id, user, memory_scale=1.0, next_dest=None):
    # And run it.
    if user:
        user_roles = [role.name for role in user.all_roles() if not role.deleted]
        user_preferences = user.extra_preferences
        email = user.email
        user_id = user.id
    else:
        user_roles = []
        user_preferences = []
        email = ''
        user_id = -1

    if get_tool_id(tool_id).startswith('interactive_tool_') and user_id == -1:
        raise JobMappingException("This tool is restricted to registered users, "
                                  "please contact a site administrator")

    try:
        env, params, runner, spec, tags = _gateway(tool_id, user_preferences, user_roles, user_id, email,
                                                   ft=FAST_TURNAROUND, special_tools=SPECIAL_TOOLS,
                                                   memory_scale=memory_scale)
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
        tags=tags,
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
