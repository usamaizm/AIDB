#!/usr/bin/env python3
"""Check completeness of declared AIDB contributor metadata; not proof of authorship."""
import json, os, re, sys
from pathlib import Path

START = "<!-- AIDB_CONTRIBUTORS_START -->"
END = "<!-- AIDB_CONTRIBUTORS_END -->"
HEADER = ["agent_id", "github_actor", "attribution_status", "contribution_role", "provenance"]
ID_RE = re.compile(r"^(?:agent|human)-[a-z0-9]+(?:-[a-z0-9]+)*$")
ACTOR_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
STATUSES = {"user_confirmed", "self_declared", "maintainer_verified", "unknown"}
ROLES = {"primary", "co_author", "reviewer", "maintainer_assisted"}

def cells(line):
    return [part.strip() for part in line.strip().strip("|").split("|")]

def validate_body(body, github_author):
    if START not in body or END not in body:
        return [f"PR body must include {START} and {END}."]
    block = body.split(START, 1)[1].split(END, 1)[0]
    rows = [line.strip() for line in block.splitlines() if line.strip().startswith("|")]
    if len(rows) < 3:
        return ["Contributor table needs a header, separator, and at least one row."]
    if cells(rows[0]) != HEADER:
        return ["Contributor table header must be: " + " | ".join(HEADER)]
    contributors, errors = [], []
    for number, line in enumerate(rows[2:], 1):
        values = cells(line)
        if len(values) != len(HEADER):
            errors.append(f"Contributor row {number} must contain exactly five columns.")
        else:
            contributors.append(dict(zip(HEADER, values)))
    if not contributors:
        return errors + ["Add at least one contributor row."]
    seen, author_present = set(), False
    for number, c in enumerate(contributors, 1):
        if not ID_RE.fullmatch(c["agent_id"]):
            errors.append(f"Contributor {number}: use a stable agent- or human- prefixed kebab-case ID.")
        if not ACTOR_RE.fullmatch(c["github_actor"]):
            errors.append(f"Contributor {number}: github_actor must be a GitHub login.")
        if c["attribution_status"] not in STATUSES:
            errors.append(f"Contributor {number}: invalid attribution_status.")
        if c["contribution_role"] not in ROLES:
            errors.append(f"Contributor {number}: invalid contribution_role.")
        if len(c["provenance"]) < 8 or c["provenance"].lower() in {"todo", "tbd", "unknown"}:
            errors.append(f"Contributor {number}: provide a factual provenance note.")
        key = (c["agent_id"], c["github_actor"].lower())
        if key in seen:
            errors.append(f"Contributor {number}: duplicate contributor identity.")
        seen.add(key)
        if c["github_actor"].lower() == github_author.lower():
            author_present = True
    if not author_present:
        errors.append(f"The PR author's GitHub account ({github_author}) must appear in the table.")
    return errors

def main():
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH is not set.", file=sys.stderr); return 2
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pr = event.get("pull_request")
    if not pr:
        print("No pull_request payload found.", file=sys.stderr); return 2
    errors = validate_body(pr.get("body") or "", pr.get("user", {}).get("login", ""))
    if errors:
        print("AIDB contributor attribution validation failed:")
        for error in errors: print("- " + error)
        print("See docs/CONTRIBUTOR_PROTOCOL.md. This check does not prove authorship.")
        return 1
    print("Contributor metadata is complete. This check does not authenticate model identity or prove authorship.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
