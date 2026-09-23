"""Tests for genai_catalogue_pr.py.

Run with: python3 -m unittest discover -s bin -p 'test_genai_catalogue_pr.py'
"""

import base64
import contextlib
import datetime
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import genai_catalogue_pr as bot

LOC = (
    "\n".join(
        [
            "#Sample header, as in the real file",
            "#<value>\t<model_id>\t<name>\t<domain>\t<provider>\t<free_tag>",
            "#",
            "a1-fr\ta1\tA one (A1) [fr]\ttext\tfr\tVendor",
            "a2-fr\ta2\tA two (A2) [fr]\tmultimodal\tfr\tVendor",
            "b1-cz\tb1\tB one (B1) [cz]\tmultimodal\tcz\tVendor",
            "b2-cz\tb2\tB two (B2) [cz]\ttext\tcz\tVendor",
            "",
            "# --- Aliases: stable role/task routing names ---",
            "alias-cz\talias\tAlias [cz]\ttext\tcz\tcz",
            "",
            "# --- Embedding models (domain=embedding) ---",
            "e1-fr\te1\tE one [fr]\tembedding\tfr\tVendor",
            "e2-cz\te2:latest\tE two [cz]\tembedding\tcz\tVendor",
            "#skip-cz\tskipped\tnot wanted\ttext\tcz\tVendor",
        ]
    )
    + "\n"
)


def now_text(days_ago=0):
    """Return a report timestamp, `days_ago` days in the past."""
    when = datetime.datetime.now(datetime.timezone.utc)
    when -= datetime.timedelta(days=days_ago)
    return when.strftime("%Y-%m-%dT%H:%M:%SZ")


def report(results=(), new_models=(), days_ago=0):
    """Return a probe report."""
    return {
        "format": 1,
        "summary": {"started": now_text(days_ago)},
        "results": list(results),
        "new_models": list(new_models),
    }


def row(value, model_id, provider, status="HEALTHY", error=None):
    """Return a report entry for a catalogue row."""
    if error is None and status != "HEALTHY":
        error = f"text: HTTP 400: {model_id} is broken"
    return {
        "value": value,
        "model_id": model_id,
        "provider": provider,
        "status": status,
        "error": error,
    }


def new(model_id, provider, status="HEALTHY", domain="text", error=None):
    """Return a report entry for a model the catalogue lacks."""
    if error is None and status != "HEALTHY":
        error = f"text: HTTP 400: {model_id} is not a chat model"
    return {
        "model_id": model_id,
        "provider": provider,
        "status": status,
        "domain": domain if status == "HEALTHY" else None,
        "error": error,
    }


def added_row(value, model_id, domain, provider):
    """Return the line the bot writes for a new model."""
    name = f"{bot.MARKER}: description ({model_id}) [{provider}]"
    return "\t".join([value, model_id, name, domain, provider, bot.MARKER])


class CheckTest(unittest.TestCase):
    """The check command."""

    def test_valid_file_passes(self):
        """The fixture, like the real file, has no problems."""
        self.assertEqual(bot.check_loc(LOC), [])

    def test_short_row(self):
        """A row needs at least five columns."""
        problems = bot.check_loc(LOC + "x\ty\n")
        self.assertEqual(problems, ["line 16: 2 columns, need 5"])

    def test_unknown_domain(self):
        """The domain must be one LLM Hub or the RAG Retriever knows."""
        text = LOC.replace("\ttext\tfr\t", "\tvideo\tfr\t")
        problems = bot.check_loc(text)
        self.assertEqual(problems, ["line 4: unknown domain 'video'"])

    def test_duplicate_value(self):
        """Values are unique."""
        problems = bot.check_loc(LOC + "a1-fr\tx\tX\ttext\tfr\tV\n")
        self.assertEqual(
            problems, ["line 16: value 'a1-fr' is already used on line 4"]
        )

    def test_placeholder_in_active_row(self):
        """An active row must not keep a placeholder, unless allowed."""
        text = LOC + added_row("n-fr", "n", "text", "fr") + "\n"
        problems = bot.check_loc(text)
        self.assertEqual(
            problems, [f"line 16: fill in the {bot.MARKER} placeholders"]
        )
        self.assertEqual(bot.check_loc(text, placeholders_allowed=True), [])

    def test_placeholder_in_commented_row(self):
        """A commented-out row may keep its placeholder."""
        text = LOC + "#" + added_row("n-fr", "n", "text", "fr") + "\n"
        self.assertEqual(bot.check_loc(text), [])

    def test_check_command(self):
        """The command exits 0 for a good file and 1 for a bad one."""
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = os.path.join(tmp, "good"), os.path.join(tmp, "bad")
            with open(good, "w") as f:
                f.write(LOC)
            with open(bad, "w") as f:
                f.write(LOC + "x\n")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(bot.main(["check", good]), 0)
                self.assertEqual(bot.main(["check", bad]), 1)
            self.assertIn("line 16: 1 columns, need 5", out.getvalue())


class ApplyTest(unittest.TestCase):
    """Applying a report to the file."""

    def apply(self, results=(), new_models=(), loc=LOC, pr_loc=None):
        """Apply a report built from the entries; return (lines, changes)."""
        text, changes = bot.apply_report(
            report(results, new_models), loc, pr_loc
        )
        return text.splitlines(), changes

    def test_nothing_to_change(self):
        """Healthy rows leave the file as it is."""
        text, changes = bot.apply_report(
            report([row("a1-fr", "a1", "fr")]), LOC
        )
        self.assertEqual(text, LOC)
        self.assertFalse(changes.removed or changes.replaced or changes.added)

    def test_dead_row_removed(self):
        """A DEAD row is removed."""
        lines, changes = self.apply(
            [row("a1-fr", "a1", "fr", "DEAD"), row("a2-fr", "a2", "fr")]
        )
        self.assertNotIn(LOC.splitlines()[3], lines)
        self.assertEqual(len(lines), len(LOC.splitlines()) - 1)
        self.assertEqual(list(changes.removed), [3])

    def test_drift_row_becomes_text(self):
        """A multimodal row that rejects images becomes text."""
        lines, changes = self.apply(
            [row("a2-fr", "a2", "fr", "CAPABILITY_DRIFT")]
        )
        self.assertEqual(
            lines[4], "a2-fr\ta2\tA two (A2) [fr]\ttext\tfr\tVendor"
        )
        self.assertEqual(len(changes.retyped), 1)

    def test_drift_on_text_row_ignored(self):
        """A row that is already text is not touched."""
        lines, changes = self.apply(
            [row("a1-fr", "a1", "fr", "CAPABILITY_DRIFT")]
        )
        self.assertEqual(lines, LOC.splitlines())
        self.assertEqual(changes.retyped, [])

    def test_failing_and_unconfigured_rows_listed(self):
        """FAILING and UNCONFIGURED rows are not changed, only listed."""
        lines, changes = self.apply(
            [
                row("b1-cz", "b1", "cz", "FAILING"),
                row("b2-cz", "b2", "cz", "UNCONFIGURED"),
            ]
        )
        self.assertEqual(lines, LOC.splitlines())
        statuses = [e["status"] for e in changes.attention]
        self.assertEqual(statuses, ["FAILING", "UNCONFIGURED"])

    def test_row_found_by_model_when_value_changed(self):
        """A renamed value still finds the one row with that model."""
        lines, _ = self.apply(
            [row("old-a1", "a1", "fr", "DEAD"), row("a2-fr", "a2", "fr")]
        )
        self.assertNotIn(LOC.splitlines()[3], lines)

    def test_ambiguous_row_left_alone(self):
        """With two rows for one model and no matching value, none goes."""
        loc = (
            LOC
            + "x1-fr\tx\tX [fr]\ttext\tfr\tV\nx2-fr\tx\tX [fr]\ttext\tfr\tV\n"
        )
        lines, changes = self.apply(
            [row("other", "x", "fr", "DEAD"), row("a1-fr", "a1", "fr")],
            loc=loc,
        )
        self.assertEqual(lines, loc.splitlines())
        self.assertEqual(changes.removed, {})

    def test_row_not_in_file_ignored(self):
        """A report row the file no longer has is ignored."""
        lines, changes = self.apply(
            [row("gone-fr", "gone", "fr", "DEAD"), row("a1-fr", "a1", "fr")]
        )
        self.assertEqual(lines, LOC.splitlines())
        self.assertEqual(changes.attention, [])

    def test_provider_guard(self):
        """If every row of a provider is DEAD, none of them is removed."""
        error = "text: HTTP 401: key expired"
        lines, changes = self.apply(
            [
                row("b1-cz", "b1", "cz", "DEAD", error),
                row("b2-cz", "b2", "cz", "DEAD", error),
                row("a1-fr", "a1", "fr"),
            ]
        )
        self.assertEqual(lines, LOC.splitlines())
        self.assertEqual(changes.held_back, {"cz": error})

    def test_single_dead_row_of_provider_removed(self):
        """The guard needs at least two rows."""
        lines, changes = self.apply([row("e1-fr", "e1", "fr", "DEAD")])
        self.assertEqual(changes.held_back, {})
        self.assertNotIn(LOC.splitlines()[12], lines)

    def test_new_model_after_its_provider(self):
        """A new chat model goes after its provider's rows, section one."""
        lines, changes = self.apply(new_models=[new("a3", "fr")])
        self.assertEqual(lines[5], added_row("a3-fr", "a3", "text", "fr"))
        self.assertEqual(len(changes.added), 1)

    def test_new_model_of_new_provider(self):
        """A provider without rows gets its name as the value's ending."""
        lines, _ = self.apply(
            new_models=[new("n1", "xx", domain="multimodal")]
        )
        self.assertEqual(
            lines[7], added_row("n1-xx", "n1", "multimodal", "xx")
        )
        self.assertEqual(lines[8], "")

    def test_new_image_model_in_first_section(self):
        """Image models are chat models too."""
        lines, _ = self.apply(new_models=[new("ocr", "cz", domain="image")])
        self.assertEqual(lines[7], added_row("ocr-cz", "ocr", "image", "cz"))

    def test_new_embedding_model(self):
        """A new embedding model goes to the end of the embedding section."""
        lines, _ = self.apply(new_models=[new("e3", "fr", domain="embedding")])
        self.assertEqual(
            lines[14], added_row("e3-fr", "e3", "embedding", "fr")
        )
        self.assertTrue(lines[15].startswith("#skip-cz"))

    def test_new_embedding_model_without_section(self):
        """Without an embedding section, the row goes to the end."""
        loc = "a1-fr\ta1\tA one [fr]\ttext\tfr\tVendor\n"
        lines, _ = self.apply(
            new_models=[new("e3", "fr", domain="embedding")], loc=loc
        )
        self.assertEqual(lines[1], added_row("e3-fr", "e3", "embedding", "fr"))

    def test_value_cleaned(self):
        """Slashes become dashes and a :latest tag is dropped."""
        lines, _ = self.apply(new_models=[new("org/m:latest", "cz")])
        self.assertIn(
            added_row("org-m-cz", "org/m:latest", "text", "cz"), lines
        )

    def test_value_made_unique(self):
        """A value already in the file gets a number."""
        lines, _ = self.apply(new_models=[new("a1:latest", "fr")])
        self.assertIn(added_row("a1-fr-2", "a1:latest", "text", "fr"), lines)

    def test_known_models_not_added(self):
        """Models in the file, even commented out, are not added again."""
        lines, changes = self.apply(
            new_models=[new("skipped", "cz"), new("b1", "cz")]
        )
        self.assertEqual(lines, LOC.splitlines())
        self.assertEqual(changes.added, [])

    def test_only_working_models_added(self):
        """FAILING and DEAD models are not added; DEAD ones are listed."""
        lines, changes = self.apply(
            new_models=[
                new("flaky", "cz", "FAILING"),
                new("dead", "cz", "DEAD"),
            ]
        )
        self.assertEqual(lines, LOC.splitlines())
        self.assertEqual(len(changes.unusable), 1)
        model, hint = changes.unusable[0]
        self.assertEqual(model["model_id"], "dead")
        self.assertEqual(hint, "#dead-cz\tdead\tnot usable\t-\tcz")

    def test_hint_makes_model_known(self):
        """Pasting the suggested line stops the model being listed."""
        _, changes = self.apply(new_models=[new("dead", "cz", "DEAD")])
        loc = LOC + changes.unusable[0][1] + "\n"
        _, changes = self.apply(
            new_models=[new("dead", "cz", "DEAD")], loc=loc
        )
        self.assertEqual(changes.unusable, [])

    def test_admin_edits_kept(self):
        """New rows filled in or commented out on the PR branch are kept."""
        filled = "a3-fr\ta3\tA three (A3) [fr]\ttext\tfr\tAcme"
        skipped = "#" + added_row("n1-xx", "n1", "text", "xx")
        pr_loc = LOC + filled + "\n" + skipped + "\n"
        lines, changes = self.apply(
            new_models=[new("a3", "fr"), new("n1", "xx")], pr_loc=pr_loc
        )
        self.assertEqual(lines[5], filled)
        self.assertIn(skipped, lines)
        self.assertEqual(len(changes.added), 2)

    def test_invalid_result_refused(self):
        """If the result is not a valid file, nothing is written."""
        with self.assertRaises(bot.BotError):
            self.apply(loc=LOC + "a1-fr\tx\tX\ttext\tfr\tV\n")

    def test_missing_newline_kept_missing(self):
        """The file's last line ending is left as it was."""
        text, _ = bot.apply_report(
            report([row("a2-fr", "a2", "fr", "DEAD")]), LOC.rstrip("\n")
        )
        self.assertFalse(text.endswith("\n"))


class ReportTest(unittest.TestCase):
    """Reading the report."""

    def load(self, data, max_age_days=8):
        """Write `data` to a file and load it as a report."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "report.json")
            with open(path, "w") as f:
                json.dump(data, f)
            return bot.load_report(path, max_age_days)

    def test_current_report_accepted(self):
        """A recent report in format 1 loads."""
        self.assertEqual(self.load(report())["format"], 1)

    def test_other_format_refused(self):
        """A report in an unknown format is refused."""
        with self.assertRaisesRegex(bot.BotError, "format"):
            self.load(dict(report(), format=2))

    def test_old_report_refused(self):
        """A report older than the limit is refused."""
        with self.assertRaisesRegex(bot.BotError, "older than 8 days"):
            self.load(report(days_ago=9))

    def test_unreadable_report_refused(self):
        """Missing, garbled or incomplete reports give a clean error."""
        with self.assertRaisesRegex(bot.BotError, "not a readable report"):
            bot.load_report("/nonexistent/report.json", 8)
        with self.assertRaisesRegex(bot.BotError, "not a readable report"):
            self.load(["not", "a", "report"])
        with self.assertRaisesRegex(bot.BotError, "not a readable report"):
            self.load({"format": 1})
        with self.assertRaisesRegex(bot.BotError, "bad start time"):
            self.load({"format": 1, "summary": {"started": "yesterday"}})

    def test_report_without_new_models(self):
        """A report without new_models adds nothing."""
        data = report([row("a1-fr", "a1", "fr", "DEAD")])
        del data["new_models"]
        text, changes = bot.apply_report(self.load(data), LOC)
        self.assertEqual(changes.added, [])
        self.assertNotIn(LOC.splitlines()[3], text.splitlines())


class TextTest(unittest.TestCase):
    """The PR text."""

    def text(self, results=(), new_models=(), pr_loc=None):
        """Return the PR text for a report built from the entries."""
        data = report(results, new_models)
        _, changes = bot.apply_report(data, LOC, pr_loc)
        with mock.patch.dict(os.environ, {"BUILD_URL": ""}):
            return bot.pr_text(data, changes)

    def test_everything_listed(self):
        """Each kind of change and finding gets its section."""
        text = self.text(
            [
                row("a1-fr", "a1", "fr", "DEAD"),
                row("a2-fr", "a2", "fr", "CAPABILITY_DRIFT"),
                row("b1-cz", "b1", "cz", "FAILING"),
                row("b2-cz", "b2", "cz"),
            ],
            [new("a3", "fr"), new("dead", "cz", "DEAD")],
        )
        for heading in (
            "### Removed",
            "### Changed from `multimodal` to `text`",
            "### New models",
            "### Needs a look",
            "### Not usable",
        ):
            self.assertIn(heading, text)
        self.assertIn("- [ ] `a3` (fr) as `text`", text)
        self.assertIn("- FAILING `b1-cz`: `b1` (cz)", text)
        self.assertIn("```\n#dead-cz\tdead\tnot usable\t-\tcz\n```", text)
        self.assertNotIn("Built by", text)

    def test_checklist_follows_admin_edits(self):
        """Filled-in and commented-out rows are ticked off."""
        filled = "a3-fr\ta3\tA three (A3) [fr]\ttext\tfr\tAcme"
        skipped = "#" + added_row("n1-xx", "n1", "text", "xx")
        text = self.text(
            new_models=[new("a3", "fr"), new("n1", "xx")],
            pr_loc=LOC + filled + "\n" + skipped + "\n",
        )
        self.assertIn("- [x] `a3` (fr) as `text`", text)
        self.assertIn("- [x] `n1` (xx) as `text` (commented out)", text)

    def test_held_back_provider_explained(self):
        """A provider held back by the guard is explained."""
        error = "text: HTTP 401: key expired"
        text = self.text(
            [
                row("b1-cz", "b1", "cz", "DEAD", error),
                row("b2-cz", "b2", "cz", "DEAD", error),
            ]
        )
        self.assertIn("Every row of `cz` is DEAD", text)
        self.assertNotIn("### Removed", text)

    def test_nothing_to_change(self):
        """A healthy report says so."""
        text = self.text([row("a1-fr", "a1", "fr")])
        self.assertIn("needs to change this week", text)

    def test_build_url(self):
        """The Jenkins build is linked when known."""
        data = report()
        _, changes = bot.apply_report(data, LOC)
        with mock.patch.dict(os.environ, {"BUILD_URL": "https://ci/job/1/"}):
            text = bot.pr_text(data, changes)
        self.assertIn("Built by https://ci/job/1/", text)

    def test_repeated_error_said_once(self):
        """The same message from every call is shown once."""
        same = "; ".join(
            f"{kind}: HTTP 404: no such model"
            for kind in ("text", "image", "embedding")
        )
        mixed = "text: HTTP 400: chat only; image: HTTP 404: no such model"
        self.assertEqual(
            bot.short_error(same), "every call: HTTP 404: no such model"
        )
        self.assertEqual(bot.short_error(mixed), mixed)
        self.assertEqual(
            bot.short_error("text: HTTP 400: x"), "text: HTTP 400: x"
        )
        self.assertIsNone(bot.short_error(None))


class FakeGitHub:
    """Answers GitHub calls from a table and records them."""

    def __init__(self, answers=None):
        """Keep answers keyed by (method, path without the query)."""
        self.repo = bot.REPO
        self.answers = answers or {}
        self.calls = []

    def call(self, method, path, data=None, missing_ok=False):
        """Record the call; return the canned answer, None by default."""
        self.calls.append((method, path, data))
        return self.answers.get((method, path.split("?")[0]))

    def data(self, method, path):
        """Return the data sent with the first matching call."""
        for call_method, call_path, data in self.calls:
            if (call_method, call_path) == (method, path):
                return data
        raise AssertionError(f"no {method} {path} in {self.calls}")

    def made(self, method, path):
        """Tell whether a call was made."""
        return any(c[:2] == (method, path) for c in self.calls)


REF = f"/git/ref/heads/{bot.BRANCH}"
REFS = f"/git/refs/heads/{bot.BRANCH}"
COMMIT_ANSWERS = {
    ("GET", "/git/commits/base"): {"tree": {"sha": "tree0"}},
    ("POST", "/git/trees"): {"sha": "tree1"},
    ("POST", "/git/commits"): {"sha": "commit1"},
}


class PublishTest(unittest.TestCase):
    """Publishing to GitHub."""

    def test_first_run_opens_draft_pr(self):
        """Without branch or PR, both are created; the PR is a draft."""
        github = FakeGitHub(
            {**COMMIT_ANSWERS, ("POST", "/pulls"): {"html_url": "u9"}}
        )
        url = bot.publish(github, "base", "new text\n", "T", "B", None)
        self.assertEqual(url, "u9")
        tree = github.data("POST", "/git/trees")
        self.assertEqual(tree["base_tree"], "tree0")
        self.assertEqual(
            tree["tree"],
            [
                {
                    "path": bot.LOC_PATH,
                    "mode": "100644",
                    "type": "blob",
                    "content": "new text\n",
                }
            ],
        )
        commit = github.data("POST", "/git/commits")
        self.assertEqual(commit["parents"], ["base"])
        self.assertNotIn("author", commit)
        self.assertEqual(
            github.data("POST", "/git/refs"),
            {"ref": f"refs/heads/{bot.BRANCH}", "sha": "commit1"},
        )
        pr = github.data("POST", "/pulls")
        self.assertEqual(
            (pr["head"], pr["base"], pr["draft"], pr["title"], pr["body"]),
            (bot.BRANCH, "master", True, "T", "B"),
        )

    def test_later_run_updates_branch_and_pr(self):
        """An existing branch is forced to the new commit; the PR edited."""
        github = FakeGitHub({**COMMIT_ANSWERS, ("GET", REF): {"ref": 1}})
        open_pr = {"number": 7, "html_url": "u7"}
        url = bot.publish(github, "base", "new text\n", "T", "B", open_pr)
        self.assertEqual(url, "u7")
        self.assertEqual(
            github.data("PATCH", REFS), {"sha": "commit1", "force": True}
        )
        self.assertEqual(
            github.data("PATCH", "/pulls/7"), {"title": "T", "body": "B"}
        )
        self.assertFalse(github.made("POST", "/pulls"))
        self.assertFalse(github.made("POST", "/git/refs"))

    def test_withdraw_closes_pr_and_deletes_branch(self):
        """With nothing to change, the PR is closed and the branch goes."""
        github = FakeGitHub({("GET", REF): {"ref": 1}})
        bot.withdraw(github, {"number": 7, "html_url": "u7"})
        self.assertTrue(github.made("POST", "/issues/7/comments"))
        self.assertEqual(github.data("PATCH", "/pulls/7"), {"state": "closed"})
        self.assertTrue(github.made("DELETE", REFS))

    def test_withdraw_with_nothing_open(self):
        """Without PR or branch, nothing is closed or deleted."""
        github = FakeGitHub()
        bot.withdraw(github, None)
        self.assertEqual([c[0] for c in github.calls], ["GET"])


class BuildTest(unittest.TestCase):
    """The build command, end to end."""

    def setUp(self):
        """Create a work directory with a copy of the fixture file."""
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.loc = self.path("genai_models.loc", LOC)
        self.body = os.path.join(self.tmp.name, "pr_body.md")

    def path(self, name, text):
        """Write a file in the work directory; return its path."""
        path = os.path.join(self.tmp.name, name)
        with open(path, "w") as f:
            f.write(text)
        return path

    def args(self, data, *extra):
        """Write the report; return the build command's arguments."""
        report_path = self.path("report.json", json.dumps(data))
        return [
            "build",
            "--report",
            report_path,
            "--loc",
            self.loc,
            "--body",
            self.body,
            *extra,
        ]

    def read(self, path):
        """Return a file's text."""
        with open(path) as f:
            return f.read()

    def run_build(self, argv, github):
        """Run the build with a fake GitHub; return its exit status."""
        with contextlib.redirect_stdout(io.StringIO()):
            return bot.build(bot.parse_args(argv), github)

    def test_dry_run(self):
        """Without --publish, the file and the PR text are written."""
        argv = self.args(report([row("a1-fr", "a1", "fr", "DEAD")]))
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(bot.main(argv), 0)
        self.assertNotIn("a1-fr", self.read(self.loc))
        self.assertIn("### Removed", self.read(self.body))

    def test_old_report_changes_nothing(self):
        """A refused report leaves the file alone and exits 1."""
        argv = self.args(
            report([row("a1-fr", "a1", "fr", "DEAD")], days_ago=9)
        )
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(bot.main(argv), 1)
        self.assertEqual(self.read(self.loc), LOC)

    def test_missing_file_gives_clean_error(self):
        """A missing input file ends with an error line, not a traceback."""
        argv = self.args(report())
        argv[argv.index("--loc") + 1] = os.path.join(self.tmp.name, "nope")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(bot.main(argv), 1)
        self.assertTrue(err.getvalue().startswith("error: "))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(bot.main(["check", "/nonexistent/file"]), 1)

    def test_publish_needs_token(self):
        """--publish without GITHUB_TOKEN fails before touching anything."""
        argv = self.args(report(), "--publish", "--base-sha", "base")
        with mock.patch.dict(os.environ, {"GITHUB_TOKEN": ""}):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(bot.main(argv), 1)
        self.assertFalse(os.path.exists(self.body))

    def test_publish_needs_base_sha(self):
        """Publishing needs the master commit the file comes from."""
        argv = self.args(report(), "--publish")
        with mock.patch.dict(os.environ, {"GIT_COMMIT": ""}):
            args = bot.parse_args(argv)
        with self.assertRaisesRegex(bot.BotError, "base-sha"):
            bot.build(args, FakeGitHub())

    def test_publish_keeps_admin_edits(self):
        """The rebuilt branch keeps the admin's filled-in new row."""
        filled = "a3-fr\ta3\tA three (A3) [fr]\ttext\tfr\tAcme"
        branch_text = LOC + filled + "\n"
        content = base64.b64encode(branch_text.encode()).decode()
        github = FakeGitHub(
            {
                **COMMIT_ANSWERS,
                ("GET", "/pulls"): [{"number": 7, "html_url": "u7"}],
                ("GET", f"/contents/{bot.LOC_PATH}"): {"content": content},
                ("GET", REF): {"ref": 1},
            }
        )
        data = report([row("a1-fr", "a1", "fr", "DEAD")], [new("a3", "fr")])
        argv = self.args(data, "--publish", "--base-sha", "base")
        self.assertEqual(self.run_build(argv, github), 0)
        committed = github.data("POST", "/git/trees")["tree"][0]["content"]
        self.assertIn(filled, committed.splitlines())
        self.assertNotIn(LOC.splitlines()[3], committed.splitlines())
        self.assertEqual(committed, self.read(self.loc))
        self.assertTrue(github.made("PATCH", "/pulls/7"))

    def test_publish_with_nothing_to_change_closes_pr(self):
        """A healthy report closes the open bot PR."""
        github = FakeGitHub(
            {
                ("GET", "/pulls"): [{"number": 7, "html_url": "u7"}],
                ("GET", REF): {"ref": 1},
            }
        )
        argv = self.args(
            report([row("a1-fr", "a1", "fr")]), "--publish", "--base-sha", "b"
        )
        self.assertEqual(self.run_build(argv, github), 0)
        self.assertEqual(github.data("PATCH", "/pulls/7"), {"state": "closed"})
        self.assertFalse(github.made("POST", "/git/commits"))


if __name__ == "__main__":
    unittest.main()
