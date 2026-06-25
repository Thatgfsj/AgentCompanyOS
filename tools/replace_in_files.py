#!/usr/bin/env python3
"""
Replace text in files WITHOUT touching encoding.

Usage: python replace_in_files.py "SEARCH" "REPLACE" file1 [file2 ...]

Reads each file as UTF-8, replaces as plain text, writes back as UTF-8 with
no BOM. Use this instead of PowerShell Set-Content -Replace, which on
Windows reinterprets UTF-8 bytes through the system codepage and produces
mojibake for any non-ASCII characters.
"""
import sys
from pathlib import Path

def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__, file=sys.stderr)
        return 1

    search, replace = sys.argv[1], sys.argv[2]
    targets = sys.argv[3:]
    total = 0
    for path_str in targets:
        p = Path(path_str)
        text = p.read_text(encoding="utf-8")
        if search not in text:
            continue
        new_text = text.replace(search, replace)
        p.write_text(new_text, encoding="utf-8", newline="")
        n = text.count(search)
        total += n
        print(f"  {p}: {n} replacement(s)")
    print(f"Total: {total} replacement(s) across {len(targets)} file(s)")
    return 0

if __name__ == "__main__":
    sys.exit(main())