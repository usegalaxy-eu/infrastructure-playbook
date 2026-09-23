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

FAILING and UNCONFIGURED rows are never changed. If every row of a provider
is DEAD, the bot assumes a key or proxy problem and removes none of them.
What the bot leaves alone is listed in the PR text.

Commands:

  check FILE  validate a genai_models.loc file: at least five columns, a
              known domain, unique values, no placeholder left in an active
              row
  build ...   rewrite genai_models.loc in place from a report and write the
              PR text; with --publish, also update the bot's pull request

Publishing needs GITHUB_TOKEN. Every run rebuilds the branch
genai-catalogue-bot from master and opens or updates one draft PR. New rows
an admin already edited on that branch, filled in or commented out, are
kept; any other edit on the branch is lost. When there is nothing to change,
the bot's PR is closed and its branch deleted.

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

Without the GitHub credential every run is a dry run. With it, the commit is
made through the GitHub API on top of $GIT_COMMIT (the master commit Jenkins
checked out), so it is authored by the App. The App needs read and write
access to Contents and Pull requests of this repository only.

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
REPORT_FORMAT = 1
REPO = "usegalaxy-eu/infrastructure-playbook"
LOC_PATH = "files/galaxy/config/llm/genai_models.loc"
BRANCH = "genai-catalogue-bot"
BASE_BRANCH = "master"
API = "https://api.github.com"


class BotError(Exception):
    """The input or the result is unusable; nothing is published."""


def row_columns(line):
    """Return the columns of an active row, or None for comments and blanks."""
    text = line.strip()
    if not text or text.startswith("#"):
        return None
    return text.split("\t")


def commented_columns(line):
    """Return the columns of a commented-out row, or None."""
    text = line.strip()
    if not text.startswith("#"):
        return None
    columns = text.lstrip("#").strip().split("\t")
    return columns if len(columns) >= 5 else None


def check_loc(text, placeholders_allowed=False):
    """Return the problems of a genai_models.loc text, one string each."""
    problems, first_seen = [], {}
    for num, line in enumerate(text.splitlines(), 1):
        columns = row_columns(line)
        if columns is None:
            continue
        if len(columns) < 5:
            problems.append(f"line {num}: {len(columns)} columns, need 5")
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


class Catalogue:
    """The lines of a genai_models.loc file, with its rows indexed."""

    def __init__(self, text):
        """Split the text into lines and index active and commented rows."""
        self.lines = text.splitlines()
        self.trailing_newline = text.endswith("\n")
        self.rows = {}  # line index -> columns, active rows only
        self.known = {}  # (provider, model id) -> line, also commented rows
        self.values = set()
        for index, line in enumerate(self.lines):
            active = row_columns(line)
            columns = active if active is not None else commented_columns(line)
            if columns is None or len(columns) < 5:
                continue
            if active is not None:
                self.rows[index] = columns
            self.known.setdefault((columns[4], columns[1]), line.rstrip())
            self.values.add(columns[0])

    def find(self, entry):
        """Return the line index of the active row a report entry means."""
        key = (entry["provider"], entry["model_id"])
        same = [i for i, c in self.rows.items() if (c[4], c[1]) == key]
        for index in same:
            if self.rows[index][0] == entry.get("value"):
                return index
        return same[0] if len(same) == 1 else None

    def suffix(self, provider):
        """Return the ending the provider's values add to the model id."""
        endings = collections.Counter()
        for columns in self.rows.values():
            value, base = columns[0], base_value(columns[1])
            if columns[4] == provider and value.startswith(base):
                endings[value[len(base) :]] += 1
        endings.pop("", None)
        if endings:
            return endings.most_common(1)[0][0]
        return f"-{provider}"

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
    held_back: dict = dataclasses.field(default_factory=dict)
    unusable: list = dataclasses.field(default_factory=list)


def held_back_providers(results):
    """Return {provider: error} for providers whose every row is DEAD."""
    by_provider = collections.defaultdict(list)
    for entry in results:
        by_provider[entry["provider"]].append(entry)
    held_back = {}
    for provider, entries in by_provider.items():
        if len(entries) >= 2 and all(e["status"] == "DEAD" for e in entries):
            errors = collections.Counter(e.get("error") for e in entries)
            held_back[provider] = errors.most_common(1)[0][0]
    return held_back


def plan_rows(results, catalogue, changes):
    """Record the removals and domain changes the row results call for."""
    changes.held_back = held_back_providers(results)
    for entry in results:
        index = catalogue.find(entry)
        if index is None or entry["provider"] in changes.held_back:
            continue
        status = entry["status"]
        if status in ("FAILING", "UNCONFIGURED"):
            changes.attention.append(entry)
        elif status == "DEAD":
            changes.removed[index] = entry
        elif status == "CAPABILITY_DRIFT":
            columns = list(catalogue.rows[index])
            if columns[3] == "multimodal":
                columns[3] = "text"
                changes.replaced[index] = "\t".join(columns)
                changes.retyped.append(entry)


def new_row(model, value):
    """Return the line the bot proposes for a new model."""
    model_id, provider = model["model_id"], model["provider"]
    name = f"{MARKER}: description ({model_id}) [{provider}]"
    return "\t".join(
        [value, model_id, name, model["domain"], provider, MARKER]
    )


def unique(value, taken):
    """Return `value`, or it with -2, -3, ... appended if already taken."""
    candidate, number = value, 1
    while candidate in taken:
        number += 1
        candidate = f"{value}-{number}"
    return candidate


def plan_new_models(new_models, catalogue, pr_catalogue, changes):
    """Record the rows to add for working models the catalogue lacks."""
    taken = set(catalogue.values)
    carried = pr_catalogue.known if pr_catalogue else {}
    for model in new_models:
        key = (model["provider"], model["model_id"])
        if key in catalogue.known:
            continue
        value = base_value(model["model_id"])
        value += catalogue.suffix(model["provider"])
        if model["status"] == "DEAD":
            hint = "\t".join(
                [value, model["model_id"], "not usable", "-", key[0]]
            )
            changes.unusable.append((model, f"#{hint}"))
        if model["status"] != "HEALTHY":
            continue
        line = carried.get(key) or new_row(model, unique(value, taken))
        taken.add(line.lstrip("#").split("\t")[0])
        anchor = catalogue.insert_after(model["domain"], model["provider"])
        changes.inserted[anchor].append(line)
        changes.added.append((model, line))


def apply_report(report, loc_text, pr_loc_text=None):
    """Return the rewritten file text and the changes behind it."""
    catalogue = Catalogue(loc_text)
    pr_catalogue = Catalogue(pr_loc_text) if pr_loc_text else None
    changes = Changes()
    plan_rows(report.get("results", []), catalogue, changes)
    plan_new_models(
        report.get("new_models", []), catalogue, pr_catalogue, changes
    )
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
            f"{max_age_days:g} days; is the probe still running?"
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
            "The bot rebuilds this PR from each Monday's report. New rows "
            "that were filled in or commented out here are kept; any other "
            "edit on this branch is lost.",
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
        for model, line in changes.added:
            item = f"{label(model)} as `{model['domain']}`"
            if line.startswith("#"):
                out.append(f"- [x] {item} (commented out)")
            else:
                done = " " if MARKER in line else "x"
                out.append(f"- [{done}] {item}")
        out.append("")
    if changes.attention or changes.held_back:
        out += ["### Needs a look", "", "The bot did not change these:", ""]
        for entry in changes.attention:
            out.append(f"- {entry['status']} {label(entry)}: {entry['error']}")
        for provider, error in changes.held_back.items():
            out.append(
                f"- Every row of `{provider}` is DEAD ({error}). That looks "
                "like a key or proxy problem, so none was removed."
            )
        out.append("")
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


def branch_file(github, branch, path):
    """Return the text of a file on a branch, or None if it is not there."""
    data = github.call(
        "GET", f"/contents/{path}?ref={branch}", missing_ok=True
    )
    if not data:
        return None
    return base64.b64decode(data["content"]).decode("utf-8")


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


def withdraw(github, open_pr):
    """Close the bot's PR and delete its branch: nothing needs changing."""
    if open_pr:
        number = open_pr["number"]
        github.call(
            "POST",
            f"/issues/{number}/comments",
            {"body": "The latest probe report needs no changes; closing."},
        )
        github.call("PATCH", f"/pulls/{number}", {"state": "closed"})
    if branch_exists(github):
        github.call("DELETE", f"/git/refs/heads/{BRANCH}")


def build(args, github=None):
    """Apply a report, write the file and the PR text, maybe publish."""
    report = load_report(args.report, args.max_age_days)
    with open(args.loc, encoding="utf-8") as f:
        loc_text = f.read()
    open_pr, pr_loc_text = None, None
    if github:
        if not args.base_sha:
            raise BotError("--publish needs --base-sha or GIT_COMMIT")
        open_pr = find_bot_pr(github)
        if open_pr:
            pr_loc_text = branch_file(github, BRANCH, LOC_PATH)
    elif args.pr_loc:
        with open(args.pr_loc, encoding="utf-8") as f:
            pr_loc_text = f.read()

    text, changes = apply_report(report, loc_text, pr_loc_text)
    body = pr_text(report, changes)
    with open(args.loc, "w", encoding="utf-8") as f:
        f.write(text)
    with open(args.body, "w", encoding="utf-8") as f:
        f.write(body)
    print(
        f"{len(changes.removed)} removed, {len(changes.retyped)} changed to "
        f"text, {len(changes.added)} added, "
        f"{len(changes.attention) + len(changes.held_back)} need a look; "
        f"wrote {args.loc} and {args.body}"
    )

    if not github:
        print("Dry run: nothing published.")
    elif text == loc_text:
        withdraw(github, open_pr)
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
        help="the file on the bot's branch, to keep admin edits "
        "(fetched from GitHub with --publish)",
    )
    build_cmd.add_argument(
        "--max-age-days",
        type=float,
        default=8,
        help="refuse reports older than this",
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
