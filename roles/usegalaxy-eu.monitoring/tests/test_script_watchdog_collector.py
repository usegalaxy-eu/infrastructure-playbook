"""Tests for the systemd script watchdog collector template."""

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
    Path(__file__).parents[1] / "templates" / "script-watchdog-collector.py.j2"
)


def load_collector():
    """Load the collector template as a Python module."""
    loader = importlib.machinery.SourceFileLoader(
        "script_watchdog_collector", str(SCRIPT)
    )
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class ScriptWatchdogCollectorTests(unittest.TestCase):
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
        self.assertIn("running=0i", line)

    def test_running_service_emits_tick_counters(self):
        """A running service emits summed utime/stime ticks."""
        properties = {
            "LoadState": "loaded",
            "ActiveState": "active",
            "SubState": "running",
            "ControlGroup": "/system.slice/galaxy-cleanup.service",
        }
        with mock.patch.object(
            self.collector, "service_properties", return_value=properties
        ), mock.patch.object(
            self.collector, "cgroup_pids", return_value=[10, 11]
        ), mock.patch.object(
            self.collector, "process_ticks", side_effect=[(100, 50), (10, 5)]
        ):
            line = self.emit("galaxy-cleanup.service")

        self.assertIn("active_state=active", line)
        self.assertIn("running=1i", line)
        self.assertIn("processes=2i", line)
        self.assertIn("utime_ticks=110i", line)
        self.assertIn("stime_ticks=55i", line)

    def test_vanished_pid_omits_tick_fields(self):
        """A pid gone mid-scrape suppresses tick fields for this round."""
        properties = {
            "LoadState": "loaded",
            "ActiveState": "active",
            "SubState": "running",
            "ControlGroup": "/system.slice/galaxy-cleanup.service",
        }
        with mock.patch.object(
            self.collector, "service_properties", return_value=properties
        ), mock.patch.object(
            self.collector, "cgroup_pids", return_value=[10, 11]
        ), mock.patch.object(
            self.collector, "process_ticks", side_effect=[(100, 50), None]
        ):
            line = self.emit("galaxy-cleanup.service")

        self.assertNotIn("utime_ticks", line)
        self.assertNotIn("stime_ticks", line)
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

    def test_process_ticks_reads_fields_14_and_15(self):
        """process_ticks returns utime and stime from a real /proc stat."""
        pid = os.getpid()
        stat = Path(f"/proc/{pid}/stat").read_text()
        expected = stat[stat.rfind(")") + 2 :].split()
        ticks = self.collector.process_ticks(pid)
        self.assertEqual(ticks, (int(expected[11]), int(expected[12])))

    def test_process_ticks_handles_missing_pid(self):
        """A missing process yields None for the tick pair."""
        self.assertIsNone(self.collector.process_ticks(999999999))

    def test_main_requires_a_service_argument(self):
        """main() refuses to run without a service argument."""
        with mock.patch.object(
            self.collector.sys, "argv", ["script-watchdog-collector"]
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
