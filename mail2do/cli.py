#!/usr/bin/env python3
"""
mail2do main CLI: run the full pipeline end-to-end.
"""

import subprocess
import sys
from pathlib import Path

def run(cmd, outfile=None):
    """
    Helper: execute *cmd*. If *outfile* is provided, redirect stdout there;
    otherwise inherit the parent’s stdout/stderr.
    """
    try:
        if outfile is None:
            subprocess.run(cmd, check=True)
        else:
            with open(outfile, "w", encoding="utf-8") as out:
                subprocess.run(cmd, check=True, stdout=out)
    except subprocess.CalledProcessError as e:
        sys.exit(f"Command {e.cmd!r} failed with exit code {e.returncode}")

def main():
    """
    Execute the full mail2do pipeline:
      1. fetch emails  → emails.json
      2. get schema    → schema.json
      3. parse emails  → tasks.json        (script writes its own file)
      4. upload tasks  → upload_results.json
    """
    # 1. fetch emails
    run(["mail2do-fetch-emails"], "emails.json")

    # 2. notion schema
    run(["mail2do-get-schema"], "schema.json")

    # 3. parse emails – script itself writes tasks.json
    run(
        ["mail2do-parse-emails", "emails.json", "schema.json", "-o", "tasks.json"],
        outfile=None,
    )

    # 4. upload to Notion – keep a log of what was created/updated
    run(["mail2do-upload", "tasks.json"], "upload_results.json")

if __name__ == "__main__":
    main()
