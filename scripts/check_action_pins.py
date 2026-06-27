#!/usr/bin/env python3
"""Fail the build if any GitHub Action `uses:` is not pinned to a full commit SHA.

§4.9 requires every Action to be pinned to a full 40-character commit SHA —
mutable tags (``@v4``, ``@main``) have been weaponised via tag re-pointing.
This is a self-contained lint (no third-party action / tool to vet or pin in
turn), run on every PR that touches a workflow and on the weekly scan.

Exemptions: local actions (``./`` or ``../``) and ``docker://`` image refs,
which are not tag-mutable in the same way.
"""

from __future__ import annotations

import pathlib
import re
import sys

SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
USES_RE = re.compile(r"""^\s*-?\s*uses:\s*["']?([^"'\s#]+)["']?""")
WORKFLOW_DIR = pathlib.Path(".github/workflows")


def main() -> int:
    problems: list[tuple[pathlib.Path, int, str, str]] = []
    for wf in sorted(WORKFLOW_DIR.rglob("*.y*ml")):
        for lineno, line in enumerate(wf.read_text().splitlines(), start=1):
            m = USES_RE.match(line)
            if not m:
                continue
            ref = m.group(1)
            if ref.startswith(("./", "../", "docker://")):
                continue
            if "@" not in ref:
                problems.append((wf, lineno, ref, "missing @<sha>"))
                continue
            sha = ref.rsplit("@", 1)[1]
            if not SHA_RE.match(sha):
                problems.append((wf, lineno, ref, "ref is not a 40-char commit SHA"))

    for wf, lineno, ref, why in problems:
        print(f"::error file={wf},line={lineno}::Action not SHA-pinned ({why}): {ref}")

    if problems:
        print(
            f"\n{len(problems)} unpinned action reference(s). Pin every `uses:` to a "
            "full 40-character commit SHA (keep a `# vX.Y.Z` comment for readability)."
        )
        return 1
    print("OK: every GitHub Action is pinned to a full commit SHA.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
