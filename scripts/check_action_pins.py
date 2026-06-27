#!/usr/bin/env python3
"""Fail the build if any GitHub Action `uses:` is not pinned to a full commit SHA.

§4.9 requires every Action to be pinned to a full 40-character commit SHA —
mutable tags (``@v4``, ``@main``) have been weaponised via tag re-pointing.
This is a self-contained lint (no third-party action / tool to vet or pin in
turn), run on every PR that touches a workflow and on the weekly scan.

Exemption: only local actions (``./`` or ``../``). ``docker://`` image refs use
mutable tags and must be pinned (by digest) too, so they are NOT exempt.
"""

from __future__ import annotations

import pathlib
import re
import sys

# A pinned ref is either a full 40-char git commit SHA (GitHub Actions) or a
# sha256 OCI image digest (``docker://image@sha256:<64 hex>``). Both are
# immutable; mutable tags (``@v4``, ``@latest``, no ``@``) are not.
SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-fA-F]{64}$")
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
            # Only local composite actions are exempt; docker:// refs are
            # tag-mutable and must be pinned, so they fall through to the check.
            if ref.startswith(("./", "../")):
                continue
            if "@" not in ref:
                problems.append((wf, lineno, ref, "missing @<commit-sha|sha256-digest>"))
                continue
            pin = ref.rsplit("@", 1)[1]
            if not (SHA_RE.match(pin) or DIGEST_RE.match(pin)):
                problems.append(
                    (wf, lineno, ref, "ref is not a full commit SHA or sha256 digest")
                )

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
