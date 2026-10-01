import unittest
from pathlib import Path


TEMPLATES = Path(__file__).parents[1] / "templates"


class ForceRetryTemplateTests(unittest.TestCase):
    def test_timer_is_persistent_and_uses_configured_annual_schedule(self):
        timer = (TEMPLATES / "galaxy-cleanup-force-retry.timer.j2").read_text()

        self.assertIn("OnCalendar={{ galaxy_cleanup_force_retry_on_calendar }}", timer)
        self.assertIn("Persistent=true", timer)

    def test_script_runs_only_purge_datasets_with_force_retry(self):
        script = (TEMPLATES / "cleanup_force_retry.sh.j2").read_text()

        self.assertEqual(script.count("--force-retry"), 3)
        self.assertIn("purge_datasets", script)
        self.assertIn('exit "${exit_code}"', script)
        self.assertIn("pgcleanup --force-retry started", script)
        self.assertIn("pgcleanup --force-retry ${result}", script)


if __name__ == "__main__":
    unittest.main()
