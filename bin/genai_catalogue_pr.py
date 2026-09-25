#!/usr/bin/env python3
r"""Turn the GenAI catalogue probe's report into a pull request.

The probe (role usegalaxy_eu.genai_catalogue_probe) runs on maintenance every
Monday and reports which rows of genai_models.loc still work and which new
models the proxies offer. This script applies that report to a checkout of
master:

- rows the proxy rejects (DEAD) are removed,
- rows tagged multimodal that reject images (CAPABILITY_DRIFT) become text,
- working new models are added, with the description and the vendor left as
  TODO-genai-bot placeholders for an admin to fill in.

A row is only changed if master still has it as it was probed: same value,
model id, provider and domain. FAILING, UNCONFIGURED and MALFORMED rows are
never changed. Nothing is changed for a provider whose model list could not
be fetched or whose every row is DEAD, and no image row is changed for a
provider whose every image call was rejected: those look like key or proxy
problems. What the bot leaves alone is listed in the PR text.

Commands:

  check FILE  validate a genai_models.loc file: at least six columns (Galaxy
              ignores shorter rows), a known domain, unique values, no
              placeholder left in an active row
  build ...   rewrite genai_models.loc in place from a report and write the
              PR text; with --publish, also update the bot's pull request

Publishing needs GITHUB_TOKEN. Every run rebuilds the branch
genai-catalogue-bot from master and opens or updates one draft PR. Rows the
branch added are carried over if an admin filled them in or commented them
out, or if their model failed only this week; any other edit on the branch
is lost. When nothing needs to change, the bot closes its PR with a comment
listing what the report still found, and deletes the branch.

Jenkins job usegalaxy-eu/genai-catalogue-pr (freestyle):

  Restrict where this project can be run: internal-access
  Source code: https://github.com/usegalaxy-eu/infrastructure-playbook.git,
      branch master
  Build periodically: H 7 * * 1 (the probe runs on Mondays at 05:00)
  String parameter PROBE_SSH_TARGET, e.g. someone@maintenance.bi.privat
  SSH Agent: a credential that can read the report on maintenance
  Once the GitHub App exists: bind its credential as "Username and password
      (separated)" with the password variable GITHUB_TOKEN
  Execute shell:
      set -eu
      ssh -o BatchMode=yes "$PROBE_SSH_TARGET" \
          cat /var/log/genai_catalogue_probe/report.json > report.json
      python3 bin/genai_catalogue_pr.py build --report report.json \
          --loc files/galaxy/config/llm/genai_models.loc \
          --body pr_body.md ${GITHUB_TOKEN:+--publish}
      git diff > genai_models.diff
  Archive the artifacts: report.json, pr_body.md, genai_models.diff

Reports older than two days are refused, so a Monday without a probe run
fails the job instead of replaying last week's report. Without the GitHub
credential every run is a dry run. With it, the commit is made through the
GitHub API on top of $GIT_COMMIT (the master commit Jenkins checked out), so
it is authored by the App. The App needs read and write access to Contents
and Pull requests of this repository only.

Tests: python3 -m unittest discover -s bin -p 'test_genai_catalogue_pr.py'
"""

import argparse
import base64
import collections
import dataclasses
import datetime
import json
import os
import re
import sys
import urllib.error
import urllib.request

MARKER = "TODO-genai-bot"
DOMAINS = ("text", "multimodal", "image", "embedding")
GALAXY_COLUMNS = 6
REPORT_FORMAT = 1
REPO = "usegalaxy-eu/infrastructure-playbook"
LOC_PATH = "files/galaxy/config/llm/genai_models.loc"
BRANCH = "genai-catalogue-bot"
BASE_BRANCH = "master"
API = "https://api.github.com"


class BotError(Exception):
    """The input or the result is unusable; nothing is published."""


def split_lines(text):
    """Split a file at newlines only, as Galaxy does."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return lines


def row_columns(line):
    """Return the columns of an active row, or None for comments and blanks.

    Like Galaxy, a line is a comment if it starts with "#"; columns keep
    their spacing, and an empty last column is kept too.
    """
    line = line.rstrip("\r")
    if not line or line.startswith("#"):
        return None
    return line.split("\t")


def commented_columns(line):
    """Return the columns of a commented-out row, or None."""
    line = line.rstrip("\r")
    if not line.startswith("#"):
        return None
    columns = line.lstrip("#").lstrip(" ").split("\t")
    return columns if len(columns) >= 5 else None


def line_columns(line):
    """Return the columns of an active or commented-out row, or None."""
    columns = row_columns(line)
    if columns is None:
        return commented_columns(line)
    return columns if len(columns) >= 5 else None


def check_loc(text, placeholders_allowed=False):
    """Return the problems of a genai_models.loc text, one string each."""
    problems, first_seen = [], {}
    for num, line in enumerate(split_lines(text), 1):
        columns = row_columns(line)
        if columns is None:
            continue
        if len(columns) < GALAXY_COLUMNS:
            problems.append(
                f"line {num}: {len(columns)} columns; Galaxy needs "
                f"{GALAXY_COLUMNS} and ignores the row"
            )
            continue
        value, domain = columns[0], columns[3]
        if domain not in DOMAINS:
            problems.append(f"line {num}: unknown domain {domain!r}")
        if value in first_seen:
            problems.append(
                f"line {num}: value {value!r} is already used on line "
                f"{first_seen[value]}"
            )
        first_seen.setdefault(value, num)
        if MARKER in line and not placeholders_allowed:
            problems.append(f"line {num}: fill in the {MARKER} placeholders")
    return problems


def base_value(model_id):
    """Return the part of a row's value that comes from its model id."""
    if model_id.endswith(":latest"):
        model_id = model_id[: -len(":latest")]
    return re.sub(r"[^A-Za-z0-9._-]", "-", model_id)


def added_lines(old_text, new_text):
    """Return the lines of new_text that old_text does not have."""
    remaining = collections.Counter(split_lines(old_text))
    added = []
    for line in split_lines(new_text):
        if remaining[line]:
            remaining[line] -= 1
        else:
            added.append(line)
    return added


class Catalogue:
    """The lines of a genai_models.loc file, with its rows indexed."""

    def __init__(self, text):
        """Split the text into lines and index active and commented rows."""
        self.lines = split_lines(text)
        self.trailing_newline = text.endswith("\n")
        self.rows = {}  # line index -> columns, active rows only
        self.known = set()  # (provider, model id), also commented rows
        self.values = set()
        for index, line in enumerate(self.lines):
            columns = line_columns(line)
            if columns is None:
                continue
            if row_columns(line) is not None:
                self.rows[index] = columns
            self.known.add((columns[4], columns[1]))
            self.values.add(columns[0])

    def find(self, entry):
        """Return the index of the active row a report entry names, if any.

        The row must have the entry's value, model id and provider.
        """
        key = (entry.get("value"), entry["model_id"], entry["provider"])
        for index, columns in self.rows.items():
            if (columns[0], columns[1], columns[4]) == key:
                return index
        return None

    def new_value(self, provider, model_id):
        """Return a value for a new model, in the provider's style."""
        endings = collections.Counter()
        for columns in self.rows.values():
            value, base = columns[0], base_value(columns[1])
            if columns[4] == provider and value.startswith(base):
                endings[value[len(base) :]] += 1
        endings.pop("", None)
        suffix = f"-{provider}"
        if endings:
            suffix = endings.most_common(1)[0][0]
        return base_value(model_id) + suffix

    def insert_after(self, domain, provider):
        """Return the index of the line a new row goes after (-1: first)."""
        dividers = [
            i
            for i, line in enumerate(self.lines)
            if line.strip().startswith("# ---")
        ]
        if domain == "embedding":
            starts = [
                i for i in dividers if "Embedding models" in self.lines[i]
            ]
            if not starts:
                return self.last_content_line()
            start = starts[0]
            end = next((i for i in dividers if i > start), len(self.lines))
            rows = [i for i in self.rows if start < i < end]
            return rows[-1] if rows else start
        end = dividers[0] if dividers else len(self.lines)
        rows = [i for i in self.rows if i < end]
        same = [i for i in rows if self.rows[i][4] == provider]
        if same:
            return same[-1]
        return rows[-1] if rows else end - 1

    def last_content_line(self):
        """Return the index of the last non-blank line (-1: none)."""
        for index in range(len(self.lines) - 1, -1, -1):
            if self.lines[index].strip():
                return index
        return -1

    def render(self, removed, replaced, inserted):
        """Return the text with lines removed, replaced and inserted."""
        out = list(inserted.get(-1, []))
        for index, line in enumerate(self.lines):
            if index not in removed:
                out.append(replaced.get(index, line))
            out.extend(inserted.get(index, []))
        text = "\n".join(out)
        return text + "\n" if out and self.trailing_newline else text


@dataclasses.dataclass
class Changes:
    """What a report means for the catalogue."""

    removed: dict = dataclasses.field(default_factory=dict)
    replaced: dict = dataclasses.field(default_factory=dict)
    retyped: list = dataclasses.field(default_factory=list)
    inserted: dict = dataclasses.field(
        default_factory=lambda: collections.defaultdict(list)
    )
    added: list = dataclasses.field(default_factory=list)
    attention: list = dataclasses.field(default_factory=list)
    stale: list = dataclasses.field(default_factory=list)
    held_back: dict = dataclasses.field(default_factory=dict)
    image_held_back: dict = dataclasses.field(default_factory=dict)
    unusable: list = dataclasses.field(default_factory=list)
    unclassified: list = dataclasses.field(default_factory=list)


def common_error(entries):
    """Return the most frequent error message of some report entries."""
    errors = collections.Counter(
        (e.get("error") or "").split(": ", 1)[-1] for e in entries
    )
    return errors.most_common(1)[0][0]


def image_call_failed(entry):
    """Tell whether a row's image call was rejected (None: not made)."""
    if entry["status"] not in ("HEALTHY", "CAPABILITY_DRIFT", "DEAD"):
        return None
    if entry.get("domain") == "multimodal" and entry["status"] != "DEAD":
        return entry["status"] == "CAPABILITY_DRIFT"
    if entry.get("domain") == "image":
        return entry["status"] == "DEAD"
    return None


def held_back_providers(report):
    """Return {provider: reason} for providers the bot must not touch."""
    held_back = {}
    for provider, error in (report.get("listing_errors") or {}).items():
        held_back[provider] = f"its model list could not be fetched ({error})"
    by_provider = collections.defaultdict(list)
    for entry in report.get("results", []):
        by_provider[entry["provider"]].append(entry)
    for provider, entries in by_provider.items():
        dead = all(e["status"] == "DEAD" for e in entries)
        if provider not in held_back and len(entries) >= 2 and dead:
            held_back[
                provider
            ] = f"every row is DEAD ({common_error(entries)})"
    return held_back


def image_held_back_providers(results):
    """Return {provider: error} for providers whose image calls all fail."""
    by_provider = collections.defaultdict(list)
    for entry in results:
        failed = image_call_failed(entry)
        if failed is not None:
            by_provider[entry["provider"]].append((entry, failed))
    held_back = {}
    for provider, calls in by_provider.items():
        if len(calls) >= 2 and all(failed for _, failed in calls):
            held_back[provider] = common_error(e for e, _ in calls)
    return held_back


def plan_rows(report, catalogue, changes):
    """Record the removals and domain changes the row results call for."""
    results = report.get("results", [])
    changes.held_back = held_back_providers(report)
    changes.image_held_back = {
        provider: error
        for provider, error in image_held_back_providers(results).items()
        if provider not in changes.held_back
    }
    for entry in results:
        index = catalogue.find(entry)
        if index is None:
            continue
        status, provider = entry["status"], entry["provider"]
        if status in ("FAILING", "UNCONFIGURED", "MALFORMED"):
            changes.attention.append(entry)
            continue
        if status not in ("DEAD", "CAPABILITY_DRIFT"):
            continue
        if provider in changes.held_back:
            continue
        if provider in changes.image_held_back and image_call_failed(entry):
            continue
        columns = catalogue.rows[index]
        if columns[3] != entry.get("domain"):
            changes.stale.append(entry)  # changed on master since the deploy
        elif status == "DEAD":
            changes.removed[index] = entry
        elif columns[3] == "multimodal":
            columns = columns[:3] + ["text"] + columns[4:]
            changes.replaced[index] = "\t".join(columns)
            changes.retyped.append(entry)


def new_row(model, value):
    """Return the line the bot proposes for a new model."""
    model_id, provider = model["model_id"], model["provider"]
    name = f"{MARKER}: description ({model_id}) [{provider}]"
    return "\t".join(
        [value, model_id, name, model["domain"], provider, MARKER]
    )


def refreshed(line, model):
    """Return the bot's row for a model, redone if nobody edited it."""
    columns = row_columns(line)
    if columns is None:
        return line  # commented out: an admin's decision
    untouched = new_row(dict(model, domain=columns[3]), columns[0])
    return new_row(model, columns[0]) if line == untouched else line


def unique(value, taken):
    """Return `value`, or it with -2, -3, ... appended if already taken."""
    candidate, number = value, 1
    while candidate in taken:
        number += 1
        candidate = f"{value}-{number}"
    return candidate


def carried_rows(report, catalogue, branch_lines):
    """Return {(provider, model id): line} for branch rows to keep."""
    models = {(m["provider"], m["model_id"]): m for m in report["new_models"]}
    listing_failed = set(report.get("listing_errors") or {})
    kept = {}
    for line in branch_lines:
        columns = line_columns(line)
        if columns is None:
            continue
        key = (columns[4], columns[1])
        if key in catalogue.known or key in kept:
            continue
        model = models.get(key)
        if line.startswith("#"):
            kept[key] = line  # the admin decided to skip the model
        elif model is None:
            if key[0] in listing_failed:
                kept[key] = line  # the model list failed this week
        elif model["status"] == "FAILING":
            kept[key] = line  # the model failed only this week
        elif model["status"] == "HEALTHY":
            kept[key] = refreshed(line, model)
    return kept


def plan_new_models(report, catalogue, branch_lines, changes):
    """Record the rows to add for models the catalogue lacks."""
    kept = carried_rows(report, catalogue, branch_lines)
    taken = set(catalogue.values)
    taken.update(line_columns(line)[0] for line in kept.values())
    for model in sorted(
        report["new_models"], key=lambda m: (m["provider"], m["model_id"])
    ):
        key = (model["provider"], model["model_id"])
        if key in catalogue.known or key in kept:
            continue
        value = catalogue.new_value(*key)
        if model["status"] == "HEALTHY":
            value = unique(value, taken)
            taken.add(value)
            kept[key] = new_row(model, value)
        elif model["status"] == "DEAD":
            hint = "\t".join([value, key[1], "not usable", "-", key[0]])
            changes.unusable.append((model, f"#{hint}"))
        else:
            changes.unclassified.append(model)
    models = {(m["provider"], m["model_id"]): m for m in report["new_models"]}
    for key, line in sorted(kept.items()):
        domain = line_columns(line)[3]
        changes.inserted[catalogue.insert_after(domain, key[0])].append(line)
        entry = models.get(key, {"provider": key[0], "model_id": key[1]})
        changes.added.append((entry, line))


def apply_report(report, loc_text, branch_lines=()):
    """Return the rewritten file text and the changes behind it.

    branch_lines are the lines the bot's open branch adds to the file.
    """
    report = dict(report, new_models=report.get("new_models") or [])
    catalogue = Catalogue(loc_text)
    changes = Changes()
    plan_rows(report, catalogue, changes)
    plan_new_models(report, catalogue, branch_lines, changes)
    text = catalogue.render(
        changes.removed, changes.replaced, changes.inserted
    )
    problems = check_loc(text, placeholders_allowed=True)
    if problems:
        raise BotError(
            "the rewritten file is not valid:\n  " + "\n  ".join(problems)
        )
    return text, changes


def load_report(path, max_age_days, now=None):
    """Read a probe report and make sure it is in a known format and new."""
    try:
        with open(path, encoding="utf-8") as f:
            report = json.load(f)
        report_format = report.get("format")
        started = report["summary"]["started"]
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise BotError(f"{path}: not a readable report ({e!r})") from None
    if report_format != REPORT_FORMAT:
        raise BotError(
            f"{path}: report format {report_format!r}, "
            f"expected {REPORT_FORMAT}"
        )
    try:
        started = datetime.datetime.strptime(started, "%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError) as e:
        raise BotError(f"{path}: bad start time ({e})") from None
    started = started.replace(tzinfo=datetime.timezone.utc)
    now = now or datetime.datetime.now(datetime.timezone.utc)
    if now - started > datetime.timedelta(days=max_age_days):
        raise BotError(
            f"{path}: the report of {started:%Y-%m-%d} is older than "
            f"{max_age_days:g} days; did the probe run this week?"
        )
    return report


def short_error(error):
    """Say an error once if every call failed with the same message."""
    parts = (error or "").split("; ")
    messages = {part.split(": ", 1)[-1] for part in parts}
    if len(parts) > 1 and len(messages) == 1:
        return f"every call: {messages.pop()}"
    return error


def label(entry):
    """Return a short Markdown name for a row or model of the report."""
    name = f"`{entry['model_id']}` ({entry['provider']})"
    if entry.get("value"):
        name = f"`{entry['value']}`: {name}"
    return name


def pr_text(report, changes):
    """Return the Markdown description of the bot's pull request."""
    date = report["summary"]["started"][:10]
    out = [
        f"Weekly update from the GenAI catalogue probe, based on its report "
        f"of {date}.",
        "",
    ]
    if not (changes.removed or changes.replaced or changes.added):
        out += ["Nothing in `genai_models.loc` needs to change this week.", ""]
    else:
        out += [
            "The bot rebuilds this PR from each Monday's report. Rows it "
            "added are kept if they were filled in or commented out here, "
            "or if their model failed only this week; any other edit on "
            "this branch is lost.",
            "",
        ]
    if changes.removed:
        out += ["### Removed", "", "The proxy rejects these rows:", ""]
        for entry in changes.removed.values():
            out.append(f"- {label(entry)}: {entry['error']}")
        out.append("")
    if changes.retyped:
        out += [
            "### Changed from `multimodal` to `text`",
            "",
            "These rows answer text but reject images:",
            "",
        ]
        for entry in changes.retyped:
            out.append(f"- {label(entry)}: {entry['error']}")
        out.append("")
    if changes.added:
        out += [
            "### New models",
            "",
            f"Replace every `{MARKER}` (the description in the third column, "
            "the vendor in the last) before merging, or comment the row out "
            "with `#` so the bot stops proposing it.",
            "",
        ]
        for entry, line in changes.added:
            item = f"{label(entry)} as `{line_columns(line)[3]}`"
            if line.startswith("#"):
                out.append(f"- [x] {item} (commented out)")
            else:
                done = " " if MARKER in line else "x"
                out.append(f"- [{done}] {item}")
        out.append("")
    out += needs_a_look(changes)
    if changes.unusable:
        out += [
            "### Not usable",
            "",
            "The proxies offer these models, but reject chat, image and "
            "embedding calls:",
            "",
        ]
        for model, _ in changes.unusable:
            out.append(f"- {label(model)}: {short_error(model['error'])}")
        out += [
            "",
            "To stop listing them here, add these lines to "
            "`genai_models.loc`:",
            "",
            "```",
        ]
        out += [hint for _, hint in changes.unusable]
        out += ["```", ""]
    if os.environ.get("BUILD_URL"):
        out.append(f"Built by {os.environ['BUILD_URL']}")
    return "\n".join(out).rstrip() + "\n"


def needs_a_look(changes):
    """Return the PR text lines for what the bot left alone."""
    out = []
    for entry in changes.attention:
        out.append(f"- {entry['status']} {label(entry)}: {entry['error']}")
    for entry in changes.stale:
        out.append(
            f"- {label(entry)} was {entry['status']} ({entry['error']}), "
            "but its row changed on master after the probe read it."
        )
    for provider, reason in changes.held_back.items():
        out.append(
            f"- Nothing was changed for `{provider}`: {reason}. That looks "
            "like a key or proxy problem."
        )
    for provider, error in changes.image_held_back.items():
        out.append(
            f"- No image row of `{provider}` was changed: every image call "
            f"was rejected ({error}). That looks like a proxy problem."
        )
    for model in changes.unclassified:
        out.append(
            f"- New model {label(model)} could not be classified this week: "
            f"{short_error(model['error'])}"
        )
    if not out:
        return []
    return ["### Needs a look", "", "The bot did not change these:", ""] + [
        *out,
        "",
    ]


class GitHub:
    """A small client for the GitHub REST API, for one repository."""

    def __init__(self, repo, token):
        """Remember the repository ("owner/name") and the token."""
        self.repo = repo
        self.token = token

    def call(self, method, path, data=None, missing_ok=False):
        """Call the API; return the decoded reply, or None if it is empty.

        With missing_ok, a 404 also returns None instead of failing.
        """
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self.token}",
            "User-Agent": "genai-catalogue-pr",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        body = None
        if data is not None:
            body = json.dumps(data).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            f"{API}/repos/{self.repo}{path}",
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read()
        except urllib.error.HTTPError as e:
            if missing_ok and e.code == 404:
                return None
            detail = e.read().decode("utf-8", errors="replace")[:300]
            raise BotError(
                f"{method} {path}: HTTP {e.code}: {detail}"
            ) from None
        return json.loads(raw) if raw else None


def find_bot_pr(github):
    """Return the open pull request from the bot's branch, if any."""
    owner = github.repo.split("/")[0]
    pulls = github.call("GET", f"/pulls?state=open&head={owner}:{BRANCH}")
    return pulls[0] if pulls else None


def file_at(github, ref):
    """Return genai_models.loc at a branch or commit, or None."""
    data = github.call(
        "GET", f"/contents/{LOC_PATH}?ref={ref}", missing_ok=True
    )
    if not data:
        return None
    return base64.b64decode(data["content"]).decode("utf-8")


def bot_branch_lines(github):
    """Return the lines the bot's branch adds to the file ([]: no branch).

    Compared with the branch's merge base, so rows deleted from master since
    the branch was built do not count as added.
    """
    comparison = github.call(
        "GET", f"/compare/{BASE_BRANCH}...{BRANCH}", missing_ok=True
    )
    if not comparison:
        return []
    base = file_at(github, comparison["merge_base_commit"]["sha"])
    return added_lines(base or "", file_at(github, BRANCH) or "")


def branch_exists(github):
    """Tell whether the bot's branch exists."""
    ref = github.call("GET", f"/git/ref/heads/{BRANCH}", missing_ok=True)
    return ref is not None


def publish(github, base_sha, text, title, body, open_pr):
    """Commit `text` on top of base_sha to the bot's branch; open the PR.

    Returns the pull request's URL.
    """
    base = github.call("GET", f"/git/commits/{base_sha}")
    entry = {"path": LOC_PATH, "mode": "100644", "type": "blob"}
    tree = github.call(
        "POST",
        "/git/trees",
        {
            "base_tree": base["tree"]["sha"],
            "tree": [dict(entry, content=text)],
        },
    )
    message = f"Update genai_models.loc from the catalogue probe\n\n{title}"
    commit = github.call(
        "POST",
        "/git/commits",
        {"message": message, "tree": tree["sha"], "parents": [base_sha]},
    )
    if branch_exists(github):
        github.call(
            "PATCH",
            f"/git/refs/heads/{BRANCH}",
            {"sha": commit["sha"], "force": True},
        )
    else:
        github.call(
            "POST",
            "/git/refs",
            {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]},
        )
    if open_pr:
        github.call(
            "PATCH",
            f"/pulls/{open_pr['number']}",
            {"title": title, "body": body},
        )
        return open_pr["html_url"]
    pr = github.call(
        "POST",
        "/pulls",
        {
            "title": title,
            "head": BRANCH,
            "base": BASE_BRANCH,
            "body": body,
            "draft": True,
        },
    )
    return pr["html_url"]


def withdraw(github, open_pr, body):
    """Close the bot's PR and delete its branch: nothing needs changing.

    The closing comment is the PR text, so what the report found still shows.
    """
    if open_pr:
        number = open_pr["number"]
        comment = (
            f"{body}\nNothing in `genai_models.loc` needs to change, so the "
            "bot closes this PR."
        )
        github.call("POST", f"/issues/{number}/comments", {"body": comment})
        github.call("PATCH", f"/pulls/{number}", {"state": "closed"})
    if branch_exists(github):
        github.call("DELETE", f"/git/refs/heads/{BRANCH}")


def build(args, github=None):
    """Apply a report, write the file and the PR text, maybe publish."""
    report = load_report(args.report, args.max_age_days)
    with open(args.loc, encoding="utf-8") as f:
        loc_text = f.read()
    open_pr, branch_lines = None, []
    if github:
        if not args.base_sha:
            raise BotError("--publish needs --base-sha or GIT_COMMIT")
        open_pr = find_bot_pr(github)
        branch_lines = bot_branch_lines(github)
    elif args.pr_loc:
        with open(args.pr_loc, encoding="utf-8") as f:
            pr_loc_text = f.read()
        base_text = loc_text
        if args.pr_base:
            with open(args.pr_base, encoding="utf-8") as f:
                base_text = f.read()
        branch_lines = added_lines(base_text, pr_loc_text)

    text, changes = apply_report(report, loc_text, branch_lines)
    body = pr_text(report, changes)
    with open(args.loc, "w", encoding="utf-8") as f:
        f.write(text)
    with open(args.body, "w", encoding="utf-8") as f:
        f.write(body)
    looks = (
        len(changes.attention)
        + len(changes.stale)
        + len(changes.held_back)
        + len(changes.image_held_back)
        + len(changes.unclassified)
    )
    print(
        f"{len(changes.removed)} removed, {len(changes.retyped)} changed to "
        f"text, {len(changes.added)} added, {looks} need a look, "
        f"{len(changes.unusable)} not usable; wrote {args.loc} and "
        f"{args.body}"
    )

    if not github:
        print("Dry run: nothing published.")
    elif text == loc_text:
        withdraw(github, open_pr, body)
        print("Nothing to change; the bot's PR is closed if it was open.")
    else:
        date = report["summary"]["started"][:10]
        title = f"GenAI catalogue: weekly update ({date})"
        url = publish(github, args.base_sha, text, title, body, open_pr)
        print(f"Published {url}")
    return 0


def check(path):
    """Validate a file; print its problems and return the exit status."""
    with open(path, encoding="utf-8") as f:
        problems = check_loc(f.read())
    for problem in problems:
        print(f"{path}: {problem}")
    return 1 if problems else 0


def parse_args(argv=None):
    """Parse the command line."""
    parser = argparse.ArgumentParser(
        description="Turn the GenAI catalogue probe's report into a PR."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    check_cmd = commands.add_parser("check", help="validate a .loc file")
    check_cmd.add_argument("file")
    build_cmd = commands.add_parser(
        "build", help="apply a probe report and write the PR text"
    )
    build_cmd.add_argument("--report", required=True, help="the report.json")
    build_cmd.add_argument(
        "--loc", required=True, help="genai_models.loc, rewritten in place"
    )
    build_cmd.add_argument(
        "--body", required=True, help="where to write the PR text"
    )
    build_cmd.add_argument(
        "--pr-loc",
        help="dry runs: the file on the bot's branch, to keep admin edits "
        "(fetched from GitHub with --publish)",
    )
    build_cmd.add_argument(
        "--pr-base",
        help="dry runs: the master file the bot's branch started from "
        "(default: --loc)",
    )
    build_cmd.add_argument(
        "--max-age-days",
        type=float,
        default=2,
        help="refuse reports older than this (default: 2)",
    )
    build_cmd.add_argument(
        "--publish",
        action="store_true",
        help="update the bot's branch and PR (needs GITHUB_TOKEN)",
    )
    build_cmd.add_argument("--repo", default=REPO, help="owner/name")
    build_cmd.add_argument(
        "--base-sha",
        default=os.environ.get("GIT_COMMIT"),
        help="the master commit --loc comes from (default: $GIT_COMMIT)",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Run a command and return its exit status."""
    args = parse_args(argv)
    try:
        if args.command == "check":
            return check(args.file)
        github = None
        if args.publish:
            token = os.environ.get("GITHUB_TOKEN")
            if not token:
                raise BotError("--publish needs GITHUB_TOKEN")
            github = GitHub(args.repo, token)
        return build(args, github)
    except (BotError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
