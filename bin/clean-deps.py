#!/usr/bin/env python3
"""Remove Galaxy roles whose installed versions differ from requirements."""

import subprocess
from pathlib import Path

import yaml
from ansible import constants


def clean_dependencies(requirements_path, roles_paths):
    """Compare exact role names and versions using Galaxy install metadata."""
    requirements = yaml.safe_load(Path(requirements_path).read_text())
    for role in requirements["roles"]:
        expected_version = role.get("version")
        # Preserve unpinned roles and the existing policy for master branches.
        if expected_version is None or str(expected_version) == "master":
            continue

        for roles_path in roles_paths:
            install_info = (
                Path(roles_path) / role["name"] / "meta/.galaxy_install_info"
            )
            # Repository-owned roles do not have Galaxy install metadata.
            if not install_info.is_file():
                continue
            installed = yaml.safe_load(install_info.read_text()) or {}
            installed_version = installed.get("version")
            if installed_version is None:
                continue
            if str(installed_version) != str(expected_version):
                print(
                    f"Removing {role['name']}: "
                    f"{installed_version} != {expected_version}",
                    flush=True,
                )
                subprocess.run(
                    [
                        "ansible-galaxy",
                        "role",
                        "remove",
                        "--roles-path",
                        str(roles_path),
                        role["name"],
                    ],
                    check=True,
                )


if __name__ == "__main__":
    clean_dependencies("requirements.yaml", constants.DEFAULT_ROLES_PATH)
