#!/usr/bin/env python3
"""Set the board status of a milestone issue on the GitHub Project board.

Usage: python3 .claude/skills/implement-milestone/board.py M3 "In Progress"
       python3 .claude/skills/implement-milestone/board.py M3 Done --close
Statuses: Todo, In Progress, Done. Needs `gh` logged in with the `project` scope.
"""

import argparse
import json
import subprocess
import sys

OWNER = "tinkerius"
PROJECT = "2"  # https://github.com/users/tinkerius/projects/2 ("BrewberryPi")
REPO = "tinkerius/brewberrypi-app"


def gh(*args: str) -> str:
    result = subprocess.run(["gh", *args], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.exit(result.stderr.strip())
    return result.stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("milestone", help="e.g. M3")
    parser.add_argument("status", choices=["Todo", "In Progress", "Done"])
    parser.add_argument("--close", action="store_true", help="also close the issue")
    args = parser.parse_args()

    project_id = json.loads(gh("project", "view", PROJECT, "--owner", OWNER, "--format", "json"))["id"]
    fields = json.loads(gh("project", "field-list", PROJECT, "--owner", OWNER, "--format", "json"))["fields"]
    status = next(f for f in fields if f["name"] == "Status")
    option = next(o["id"] for o in status["options"] if o["name"] == args.status)
    item_list = gh("project", "item-list", PROJECT, "--owner", OWNER, "--format", "json", "--limit", "200")
    items = json.loads(item_list)["items"]
    matches = [i for i in items if i["content"].get("title", "").split(" ")[0] == args.milestone]
    if len(matches) != 1:
        sys.exit(f"expected exactly one board item for {args.milestone}, found {len(matches)}")
    item = matches[0]
    gh(
        "project",
        "item-edit",
        "--id",
        item["id"],
        "--project-id",
        project_id,
        "--field-id",
        status["id"],
        "--single-select-option-id",
        option,
    )
    if args.close:
        gh("issue", "close", str(item["content"]["number"]), "-R", REPO, "--reason", "completed")
    closed = " (closed)" if args.close else ""
    print(f"{args.milestone} (#{item['content']['number']}) -> {args.status}{closed}")


if __name__ == "__main__":
    main()
