"""Collection of functions to generate Ansible playbooks that template files.

Given an Ansible playbook, this file helps you modify it in order to produce
another playbook with the sole purpose of templating files.
"""

import glob
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

import yaml
from jinja2 import Environment, FileSystemLoader, meta

# Keys from plays to be kept in the generated playbooks
KEEP_KEYS = {
    "name",
    "hosts",
    "vars",
    "vars_files",
}

# Set the default editor to "true" create empty Ansible vaults easily
os.environ["EDITOR"] = "true"


# Tasks to execute in each play.
def templating_task(
    src: str | Path,
    dest: str | Path,
) -> dict:
    """Generate an ansible templating task.

    Args:
        src: Template file.
        dest: Templated file.

    Returns:
        Ansible templating task (in the form of a dictionary).
    """
    return {
        "name": f"Template {src}",
        "template": {
            "src": str(src),
            "dest": str(dest),
        },
    }


def get_variables(path: str | Path) -> set[str]:
    """Get names of the variables used in a Jinja template.

    Args:
        path: Path of the Jinja template.

    Returns:
        Set of variables used in the Jinja template.
    """
    path = Path(path)
    dirname = path.parent

    env = Environment(
        loader=FileSystemLoader(dirname),
        extensions=["jinja2_ansible_filters.AnsibleCoreFiltersExtension"],
    )
    source = open(path, "r").read()
    parsed_content = env.parse(source)
    variables = set(meta.find_undeclared_variables(parsed_content))

    return variables


def make_playbook(
    model: str | Path,
    templates: Iterable[tuple[str | Path, str | Path]],
) -> Path:
    """Generate a playbook from a model.

    Takes a playbook as reference, keeps the skeleton of the playbook (e.g.
    variables, and variable files) and replaces the existing tasks with
    templating tasks.

    The working directory of the model playbook will be copied to a temporary
    directory and in such directory, the newly generated playbook will replace
    the model playbook. The function returns the absolute path of the newly
    generated playbook.

    Args:
        model: Playbook to be taken as reference. The skeleton of the playbook
            is kept (keys from KEEP_KEYS, for example the vars and
            vars_files), while the existing tasks are stripped out.
        templates: Files to be templated, given as tuples where the first
            element is the path of the template and the second element the
            path of the templated file.

    Returns:
        The absolute path of the newly generated playbook.
    """
    playbook = Path(model)
    dirname = playbook.parent
    basename = playbook.name

    # copy working directory to the temporary directory and chdir into it
    directory = Path(tempfile.mkdtemp()) / "ansible"
    shutil.copytree(dirname, directory)
    playbook = directory / basename
    dirname = directory

    playbook = yaml.safe_load(open(playbook))
    for i, play in enumerate(playbook):
        # filter keys
        play = {key: value for key, value in play.items() if key in KEEP_KEYS}

        # replace vaults with empty vaults
        vault_string = "$ANSIBLE_VAULT"
        for filename in play.get("vars_files", []):
            try:
                with open(filename, "r") as file:
                    is_vault = file.read(14) == vault_string
            except FileNotFoundError:
                is_vault = False
            if is_vault:
                os.remove(directory / filename)
                subprocess.run(
                    ["ansible-vault", "create", directory / filename]
                )

        # generate a file with dummy variables
        dummy_vars = {}
        # - determinate what is already defined in group variables
        group_vars = set()
        for file_path in glob.glob(
            str(directory / "group_vars" / "**" / "*.y*ml"), recursive=True
        ):
            contents = yaml.safe_load(open(file_path))
            group_vars |= set(contents)
        # - for vars files
        dummy_vars |= {
            var: "undefined"
            for vars_file in play.get("vars_files", [])
            for var in get_variables(vars_file)
            if var not in group_vars
        }
        # - for templates
        dummy_vars |= {
            var: "undefined"
            for src, _ in templates
            for var in get_variables(src)
            if var not in group_vars
        }
        # - save generated file
        with open(directory / "dummy_vars_file.yml", "w") as file:
            yaml.dump(dummy_vars, file)

        # insert file with dummy variables at the top of the vars_files list
        play["vars_files"] = play.get("vars_files", [])
        play["vars_files"].insert(0, "dummy_vars_file.yml")

        play["tasks"] = [templating_task(src, dest) for src, dest in templates]

        playbook[i] = play

    playbook_path = (directory / basename).absolute()
    with open(playbook_path, "w") as file:
        yaml.dump(playbook, file)

    return playbook_path
