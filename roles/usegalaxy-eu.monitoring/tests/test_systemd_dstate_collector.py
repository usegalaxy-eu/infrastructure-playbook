"""Tests for the systemd D-state collector template."""

import contextlib
import importlib.machinery
import importlib.util
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = (
    Path(__file__).parents[1] / "templates" / "systemd-dstate-collector.py.j2"
)


def load_collector():
    """Load the collector template as a Python module."""
    loader = importlib.machinery.SourceFileLoader(
        "systemd_dstate_collector", str(SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class SystemdDstateCollectorTests(unittest.TestCase):
    """Cover metric emission and process/cgroup helpers of the collector."""

    @classmethod
    def setUpClass(cls):
        """Load the collector module once for all tests."""
        cls.collector = load_collector()

    def emit(self, service):
        """Run collector.emit and return its printed line protocol."""
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.collector.emit(service)
        return output.getvalue().strip()

    def test_systemctl_failure_is_reported_as_unhealthy(self):
        """A missing unit is emitted with monitor_healthy=0."""
        with mock.patch.object(
            self.collector, "service_properties", return_value=None
        ):
            line = self.emit("galaxy-cleanup.service")

        self.assertIn("active_state=unknown", line)
        self.assertIn("monitor_healthy=0i", line)
        self.assertIn("d_state=0i", line)

    def test_d_state_process_is_reported(self):
        """A D-state process in the cgroup sets d_state and its count."""
        properties = {
            "LoadState": "loaded",
            "ActiveState": "active",
            "SubState": "running",
            "ExecMainStatus": "0",
            "ControlGroup": "/system.slice/galaxy-cleanup.service",
        }
        with mock.patch.object(
            self.collector, "service_properties", return_value=properties
        ), mock.patch.object(
            self.collector, "cgroup_pids", return_value=[10, 11]
        ), mock.patch.object(
            self.collector, "process_state", side_effect=["S", "D"]
        ):
            line = self.emit("galaxy-cleanup.service")

        self.assertIn("active_state=active", line)
        self.assertIn("load_state=loaded", line)
        self.assertIn("running=1i", line)
        self.assertIn("d_state=1i", line)
        self.assertIn("d_state_processes=1i", line)
        self.assertIn("processes=2i", line)

    def test_cgroup_pids_reads_one_pid_per_line(self):
        """cgroup.procs content is parsed as one integer PID per line."""
        with tempfile.TemporaryDirectory() as directory:
            cgroup = Path(directory, "system.slice", "galaxy-cleanup.service")
            cgroup.mkdir(parents=True)
            Path(cgroup, "cgroup.procs").write_text("12\n34\n")
            with mock.patch.object(
                self.collector, "CGROUP_ROOT", Path(directory)
            ):
                pids = self.collector.cgroup_pids(
                    "/system.slice/galaxy-cleanup.service"
                )

        self.assertEqual(pids, [12, 34])

    def test_process_state_handles_missing_pid(self):
        """A missing process yields None and a live PID yields a state."""
        self.assertIsNone(self.collector.process_state(999999999))
        self.assertIsNotNone(self.collector.process_state(os.getpid()))

    def test_main_requires_a_service_argument(self):
        """main() refuses to run without a service argument."""
        with mock.patch.object(
            self.collector.sys, "argv", ["systemd-dstate-collector"]
        ), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.collector.main(), 2)

    def test_escape_tag(self):
        """Tag values escape spaces, commas, equals signs and backslashes."""
        escape = self.collector.escape_tag
        self.assertEqual(escape("a b"), "a\\ b")
        self.assertEqual(escape("a,b"), "a\\,b")
        self.assertEqual(escape("a=b"), "a\\=b")
        self.assertEqual(escape("a\\b"), "a\\\\b")


if __name__ == "__main__":
    unittest.main()
