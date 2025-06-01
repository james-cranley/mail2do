#!/usr/bin/env python3
"""
add_date.py

Utility: make sure the first line of a text file is of the form
    # Current date: YYYY-MM-DD HH:MM
If that line already exists, it is updated; otherwise it is inserted.

Can be used as:
    python add_date.py prompt.txt
or imported:
    from add_date import prepend_date
    prepend_date("prompt.txt")
"""

from datetime import datetime
import sys, pathlib, re
from typing import Union

DATE_RE = re.compile(r"^#\s*Current date:")

def prepend_date(path: Union[str, pathlib.Path]) -> None:
    path = pathlib.Path(path)
    now_str = datetime.now().strftime("# Current date: %Y-%m-%d %H:%M")
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
        if lines and DATE_RE.match(lines[0]):
            lines[0] = now_str
        else:
            lines.insert(0, now_str)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        path.write_text(now_str + "\n", encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python add_date.py <prompt-file>")
        sys.exit(1)
    prepend_date(sys.argv[1])

