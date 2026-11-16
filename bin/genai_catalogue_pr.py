#!/usr/bin/env python3
r"""Turn the GenAI catalogue probe's report into a pull request.

Applies the report of the usegalaxy_eu.genai_catalogue_probe role to master's
genai_models.loc: DEAD rows are removed, CAPABILITY_DRIFT rows are only
listed (a proxy may be mid-change, so an admin checks them), and working
new models are added with TODO-genai-bot placeholders for an admin to fill
in. A model commented out in the file is not proposed again.

With --publish (needs GITHUB_TOKEN, and GIT_COMMIT: the master commit the
file comes from) the branch genai-catalogue-bot is rebuilt from master and
one draft PR is opened or updated; when nothing needs to change, it is
closed, unless the probe could not check everything this week. Without
--publish the PR text and the diff are printed and no file is written.
`check` validates a file.

Jenkins job: node internal-access, weekly after the probe (Mondays 05:00);
GITHUB_TOKEN comes from a GitHub App credential with read and write access to
Contents and Pull requests of this repository. Its build step is
genai-catalogue-pr.sh in usegalaxy-eu/jenkins-scripts.
"""

import argparse
import collections
import datetime
import difflib
import json
import os
import re
import sys
import urllib.error
import urllib.request

MARKER = "TODO-genai-bot"
DOMAINS = (
    "text",
    "multimodal",
    "image",
    "embedding",
    "rerank",
    "audio",
    "decision",
)
# Section headings new rows of these domains go under, first match wins
SECTIONS = {
    "embedding": ("Embedding",),
    "rerank": ("Rerank", "Embedding"),
    "audio": ("Speech to text",),
    "decision": ("Decision",),
}
DECISION_HEADER = (
    "# --- Decision models (domain=decision), consumed by the decision "
    "option of the LLM Hub tool ---"
)
REPO = "usegalaxy-eu/infrastructure-playbook"
LOC_PATH = "files/galaxy/config/llm/genai_models.loc"
BRANCH = "genai-catalogue-bot"


class BotError(Exception):
    """The input or the result cannot be used; nothing is published."""


def columns(line):
    """Return the columns of a row, or None for comments and blank lines."""
    if not line or line.startswith("#"):
        return None
    return line.split("\t")


def check_loc(text, placeholders_allowed=False):
    """Return the problems of a genai_models.loc text."""
    problems, values = [], set()
    for num, line in enumerate(text.split("\n"), 1):
        row = columns(line)
        if row is None:
            continue
        if len(row) < 6:
            problems.append(f"line {num}: Galaxy needs 6 columns")
        elif row[3] not in DOMAINS:
            problems.append(f"line {num}: unknown domain {row[3]!r}")
        elif row[0] in values:
            problems.append(f"line {num}: value {row[0]!r} is used twice")
        elif MARKER in line and not placeholders_allowed:
            problems.append(f"line {num}: fill in the {MARKER} placeholders")
        values.add(row[0])
    return problems


def load_report(path, max_age_days):
    """Read the probe's report; refuse other formats and old reports."""
    try:
        with open(path, encoding="utf-8") as f:
            report = json.load(f)
        started = datetime.datetime.strptime(
            report["summary"]["started"], "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=datetime.timezone.utc)
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise BotError(f"cannot read the report {path}: {e!r}") from None
    if report.get("format") != 1:
        raise BotError(f"unknown report format in {path}")
    age = datetime.datetime.now(datetime.timezone.utc) - started
    if age > datetime.timedelta(days=max_age_days):
        raise BotError(f"the report is older than {max_age_days:g} days")
    return report


def new_value(rows, provider, model_id):
    """Return a value for a new model, ending like the provider's others."""

    def base(model):
        model = (
            model[: -len(":latest")] if model.endswith(":latest") else model
        )
        return re.sub(r"[^A-Za-z0-9._-]", "-", model)

    endings = collections.Counter(
        row[0][len(base(row[1])) :]
        for row in rows.values()
        if row[4] == provider and row[0].startswith(base(row[1]) + "-")
    )
    suffix = endings.most_common(1)[0][0] if endings else f"-{provider}"
    return base(model_id) + suffix


def insert_after(lines, rows, domain, provider):
    """Return the index of the line a new row goes after.

    Chat models go after their provider's rows in the first section, but
    never above the first row of their domain (the tools default to it),
    embedding, rerank and audio models at the end of their own section
    (rerank models in the embedding section if there is no rerank section).
    """
    dividers = [i for i, line in enumerate(lines) if line.startswith("# ---")]
    if domain in SECTIONS:
        start = next(
            (
                i
                for heading in SECTIONS[domain]
                for i in dividers
                if heading in lines[i]
            ),
            None,
        )
        if start is None:
            return max(rows, default=-1)
        end = next((i for i in dividers if i > start), len(lines))
        section = [i for i in rows if start < i < end]
        return section[-1] if section else start
    end = dividers[0] if dividers else len(lines)
    section = [i for i in rows if i < end]
    same = [i for i in section if rows[i][4] == provider]
    anchor = (same or section or [end - 1])[-1]
    first = [i for i in section if rows[i][3] == domain][:1]
    return max([anchor] + first)


def parse(text):
    """Return the lines, the rows by line index and the known models."""
    lines = text.split("\n")
    rows = {}
    for i, line in enumerate(lines):
        row = columns(line)
        if row and len(row) >= 5:
            rows[i] = row
    known = {(row[4], row[1]) for row in rows.values()}
    for line in lines:
        row = line.lstrip("#").split("\t")
        if line.startswith("#") and len(row) >= 5:
            known.add((row[4], row[1]))  # commented out: do not propose it
    return lines, rows, known


def add_decision_section(lines):
    """Return the lines with a decision header after the speech section."""
    dividers = [i for i, line in enumerate(lines) if line.startswith("# ---")]
    start = next((i for i in dividers if "Speech to text" in lines[i]), None)
    end = len(lines)
    if start is not None:
        end = next((i for i in dividers if i > start), len(lines))
    while end > 0 and not lines[end - 1].strip():
        end -= 1  # after the section's last row, before blank lines
    return lines[:end] + ["", DECISION_HEADER] + lines[end:]


def apply_report(report, text):
    """Return the new file text and what changed.

    That is the removed, drifted and added entries, and the providers whose
    verdicts were skipped.
    """
    lines, rows, known = parse(text)
    if not any(
        line.startswith("# ---") and "Decision" in line for line in lines
    ):
        if any(
            m["status"] == "HEALTHY"
            and m["domain"] == "decision"
            and (m["provider"], m["model_id"]) not in known
            for m in report.get("new_models", [])
        ):
            lines, rows, known = parse("\n".join(add_decision_section(lines)))

    # A verdict only applies if master still has the row as it was probed
    index = {(r[0], r[1], r[4], r[3]): i for i, r in rows.items()}
    removed, drifted, added = [], [], []
    drop, inserts = set(), collections.defaultdict(list)
    # With no working row, the key or URL is more likely wrong than every model
    results = report.get("results", [])
    working = {e["provider"] for e in results if e["status"] == "HEALTHY"}
    skipped = {
        e["provider"]: e["error"]
        for e in results
        if e["provider"] not in working and e["status"] != "UNCONFIGURED"
    }
    for entry in results:
        if entry["provider"] in skipped:
            continue
        key = (entry["value"], entry["model_id"])
        i = index.get(key + (entry["provider"], entry["domain"]))
        if i is None:
            continue
        if entry["status"] == "DEAD":
            drop.add(i)
            removed.append(entry)
        elif entry["status"] == "CAPABILITY_DRIFT":
            drifted.append(entry)

    values = {row[0] for row in rows.values()}
    for model in report.get("new_models", []):
        provider, model_id = model["provider"], model["model_id"]
        if model["status"] != "HEALTHY" or (provider, model_id) in known:
            continue
        value = candidate = new_value(rows, provider, model_id)
        number = 1
        while candidate in values:
            number += 1
            candidate = f"{value}-{number}"
        values.add(candidate)
        name = f"{MARKER}: description ({model_id}) [{provider}]"
        row = [candidate, model_id, name, model["domain"], provider, MARKER]
        anchor = insert_after(lines, rows, model["domain"], provider)
        inserts[anchor].append("\t".join(row))
        added.append(model)

    out = list(inserts[-1])
    for i, line in enumerate(lines):
        if i not in drop:
            out.append(line)
        out.extend(inserts[i])
    new_text = "\n".join(out)
    problems = check_loc(new_text, placeholders_allowed=True)
    if problems:
        raise BotError("the new file is not valid: " + "; ".join(problems))
    return new_text, removed, drifted, added, skipped


def short(error):
    """Return the call and HTTP status or error type of a probe error.

    The PR is public, and proxy messages can quote parts of the API key.
    """
    match = re.match(r"[^:]+: (HTTP \d+|\w+)", error or "")
    return match.group(0) if match else "error"


def pr_text(removed, drifted, added, skipped=(), unchecked=()):
    """Return the Markdown description of the bot's PR."""
    out = [
        "Update from the weekly GenAI catalogue probe. The bot rebuilds this "
        "branch every week, so fill in the placeholders and merge before the "
        "next run.",
    ]
    if removed:
        out += ["", "### Removed: the proxy rejects them", ""]
        out += [f"- `{e['value']}`: {short(e['error'])}" for e in removed]
    if drifted:
        out += [
            "",
            "### Images rejected or not read",
            "",
            "Left as they are, since the proxy may have been mid-change. "
            "If it lasts, change them to `text` by hand.",
            "",
        ]
        out += [f"- `{e['value']}`: {short(e['error'])}" for e in drifted]
    if added:
        out += [
            "",
            "### New models",
            "",
            f"Replace each `{MARKER}` (description and vendor), or comment "
            "the row out with `#` so the bot does not propose it again.",
            "",
        ]
        out += [
            f"- [ ] `{m['model_id']}` ({m['provider']}) as `{m['domain']}`"
            for m in added
        ]
    if skipped:
        out += ["", "### Left unchanged: no row of these providers works", ""]
        out += [f"- `{p}`: {short(e)}" for p, e in skipped.items()]
    if unchecked:
        out += ["", "### Could not be checked this week", ""]
        out += [
            f"- `{e['model_id']}` ({e['provider']}): {e['status']}, "
            f"{short(e['error'])}"
            for e in unchecked
        ]
    if removed or drifted or skipped or unchecked:
        out += [
            "",
            "The full errors are in the probe's report on maintenance.",
        ]
    return "\n".join(out) + "\n"


def github(method, path, data=None, missing_ok=False):
    """Call the GitHub API for this repository; return the JSON reply."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}{path}",
        data=None if data is None else json.dumps(data).encode("utf-8"),
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
    except urllib.error.HTTPError as e:
        if missing_ok and e.code == 404:
            return None
        raise BotError(f"{method} {path}: HTTP {e.code}: {e.read()[:300]!r}")
    return json.loads(body) if body else None


def open_pr():
    """Return the bot's open PR, or None."""
    owner = REPO.split("/")[0]
    pulls = github("GET", f"/pulls?state=open&head={owner}:{BRANCH}")
    return pulls[0] if pulls else None


def publish(base_sha, text, title, body):
    """Commit the file on top of base_sha to the bot's branch; open the PR.

    The commit is made through the API, so it is authored by the App.
    """
    base_tree = github("GET", f"/git/commits/{base_sha}")["tree"]["sha"]
    blob = {"path": LOC_PATH, "mode": "100644", "type": "blob"}
    tree = github(
        "POST",
        "/git/trees",
        {"base_tree": base_tree, "tree": [dict(blob, content=text)]},
    )
    commit = github(
        "POST",
        "/git/commits",
        {"message": title, "tree": tree["sha"], "parents": [base_sha]},
    )
    ref = {"sha": commit["sha"], "force": True}
    if github("GET", f"/git/ref/heads/{BRANCH}", missing_ok=True):
        github("PATCH", f"/git/refs/heads/{BRANCH}", ref)
    else:
        new_ref = {"ref": f"refs/heads/{BRANCH}", "sha": commit["sha"]}
        github("POST", "/git/refs", new_ref)
    pr = open_pr()
    if pr:
        github(
            "PATCH", f"/pulls/{pr['number']}", {"title": title, "body": body}
        )
        return pr["html_url"]
    new = {"title": title, "body": body, "head": BRANCH, "base": "master"}
    return github("POST", "/pulls", dict(new, draft=True))["html_url"]


def withdraw():
    """Close the bot's PR and delete its branch."""
    pr = open_pr()
    if pr:
        github("PATCH", f"/pulls/{pr['number']}", {"state": "closed"})
    if github("GET", f"/git/ref/heads/{BRANCH}", missing_ok=True):
        github("DELETE", f"/git/refs/heads/{BRANCH}")


def main(argv=None):
    """Run a command and return its exit status."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check").add_argument("file")
    build = commands.add_parser("build")
    build.add_argument("--report", required=True)
    build.add_argument("--loc", required=True)
    build.add_argument("--max-age-days", type=float, default=2)
    build.add_argument("--publish", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            with open(args.file, encoding="utf-8") as f:
                problems = check_loc(f.read())
            for problem in problems:
                print(problem)
            return 1 if problems else 0
        base_sha = os.environ.get("GIT_COMMIT")
        if args.publish and not (os.environ.get("GITHUB_TOKEN") and base_sha):
            raise BotError("--publish needs GITHUB_TOKEN and GIT_COMMIT")
        report = load_report(args.report, args.max_age_days)
        with open(args.loc, encoding="utf-8") as f:
            old = f.read()
        text, removed, drifted, added, skipped = apply_report(report, old)
        unchecked = [
            e
            for e in report.get("results", []) + report.get("new_models", [])
            if e["status"] in ("FAILING", "UNCONFIGURED")
            and e["provider"] not in skipped
        ]
        body = pr_text(removed, drifted, added, skipped, unchecked)
        date = report["summary"]["started"][:10]
        title = f"GenAI catalogue: weekly update ({date})"
        if not args.publish:
            print(body)
            sys.stdout.writelines(
                difflib.unified_diff(
                    old.splitlines(True),
                    text.splitlines(True),
                    args.loc,
                    args.loc + " (new)",
                )
            )
        elif text == old:
            if drifted:  # the file stays as it is, so only this log shows them
                print(body)
            # only close the PR if nothing went unseen this week
            if skipped or unchecked or report.get("unlisted"):
                print("Nothing to change, but the probe missed some models")
            else:
                withdraw()
        else:
            print(publish(base_sha, text, title, body))
    except (BotError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
