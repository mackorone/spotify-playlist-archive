#!/usr/bin/env python3

import datetime
import subprocess


def run(args):
    print("- Running: {}".format(args))
    result = subprocess.run(
        args=args,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    print("- Exited with: {}".format(result.returncode))
    return result


def main():
    print("Checking for changes")
    diff = run(["git", "diff", "--quiet"])
    has_changes = diff.returncode == 1
    if not has_changes:
        print("No changes, not pushing")
        return

    print("Staging changes")
    add = run(["git", "add", "-A"])
    if add.returncode != 0:
        raise Exception("Failed to stage changes")

    print("Committing changes")
    now = datetime.datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    message = "[skip ci] {}".format(now_str)
    commit = run(["git", "commit", "-m", message])
    if commit.returncode != 0:
        raise Exception("Failed to commit changes")

    print("Pushing changes")
    push = run(["git", "push"])
    if push.returncode != 0:
        raise Exception("Failed to push changes")

    print("Done")


if __name__ == "__main__":
    main()
