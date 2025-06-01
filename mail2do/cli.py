#!/usr/bin/env python3
"""
mail2do main CLI: run the full pipeline end-to-end.
"""

import subprocess
import sys

def main():
    """
    Execute the full mail2do pipeline:
      1. fetch emails -> emails.json
      2. get Notion schema -> schema.json
      3. parse emails -> tasks.json
      4. upload tasks -> upload_results.json
    """
    steps = [
        (["mail2do-fetch-emails"], "emails.json"),
        (["mail2do-get-schema"], "schema.json"),
        (["mail2do-parse-emails", "emails.json", "schema.json"], "tasks.json"),
        (["mail2do-upload", "tasks.json"], "upload_results.json"),
    ]
    for cmd, out_file in steps:
        try:
            with open(out_file, "w", encoding="utf-8") as out:
                subprocess.run(cmd, check=True, stdout=out)
        except subprocess.CalledProcessError as e:
            sys.exit(f"Command {e.cmd!r} failed with exit code {e.returncode}")


if __name__ == "__main__":
    main()