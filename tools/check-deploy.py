#!/usr/bin/env python3
"""Deployment guard: everything index.html references must exist AND be in git.

This exists because of the failure that shipped: the deployed page referenced
three fonts, six photographs and two logos that were never committed, so every
one of them 404'd in production while the page looked perfect on the machine
that had the files. Nothing in the build caught it, because there is no build.

Checks:

  1. every local asset the page references exists on disk;
  2. ...and is tracked by git, so GitHub Pages will actually have it;
  3. no asset is referenced with a root-absolute path (/fonts/...). The site
     is a GitHub *project* page served under /excalibur-robotics-website/, so
     a root-absolute reference points outside the site and 404s. This is also
     what vite's dev server rewrites inline-CSS font URLs into, so the check
     is what stops that dev-only rewrite from ever reaching the file;
  4. .nojekyll is present, so Pages serves the tree as-is.

Run:  python3 tools/check-deploy.py      (or: npm run check)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys

PAGE = "index.html"
EXTERNAL = ("http://", "https://", "//", "data:", "mailto:", "tel:", "#")


def referenced_assets(html: str) -> dict[str, set[str]]:
    """path -> the contexts that referenced it."""
    found: dict[str, set[str]] = {}

    def add(path: str, why: str) -> None:
        path = path.split("?")[0].split("#")[0].strip()
        if not path or path.startswith(EXTERNAL):
            return
        found.setdefault(path, set()).add(why)

    for m in re.finditer(r'\b(?:src|href)\s*=\s*["\']([^"\']+)["\']', html):
        add(m.group(1), "src/href")

    # srcset="a.avif 480w, b.avif 960w"
    for m in re.finditer(r'\bsrcset\s*=\s*["\']([^"\']+)["\']', html):
        for part in m.group(1).split(","):
            token = part.strip().split()[0] if part.strip() else ""
            add(token, "srcset")

    # url(...) inside the inline stylesheets
    for m in re.finditer(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", html):
        add(m.group(1), "css url()")

    return found


def tracked_by_git(paths: list[str]) -> set[str]:
    if not paths:
        return set()
    out = subprocess.run(
        ["git", "ls-files", "-z", "--"] + paths,
        capture_output=True, text=True, check=False,
    ).stdout
    return {p for p in out.split("\0") if p}


def main() -> int:
    if not os.path.exists(PAGE):
        print(f"{PAGE} not found — run from the repo root", file=sys.stderr)
        return 2

    html = open(PAGE, encoding="utf-8").read()
    refs = referenced_assets(html)

    missing, absolute, untracked = [], [], []
    for path, whys in sorted(refs.items()):
        why = ", ".join(sorted(whys))
        if path.startswith("/"):
            absolute.append((path, why))
            continue
        if not os.path.exists(path):
            missing.append((path, why))
            continue
        if path not in tracked_by_git([path]):
            untracked.append((path, why))

    total = 0
    for path in refs:
        if not path.startswith("/") and os.path.exists(path):
            total += os.path.getsize(path)

    print(f"references checked: {len(refs)}  ({len(missing)} missing, "
          f"{len(untracked)} untracked, {len(absolute)} root-absolute)")
    print(f"referenced asset weight: {total/1024/1024:.2f} MB")

    ok = True
    for label, items, hint in (
        ("MISSING from disk", missing, "the page will 404 on this"),
        ("NOT IN GIT", untracked, "the page will 404 in production even though it works locally"),
        ("ROOT-ABSOLUTE", absolute, "breaks under the /excalibur-robotics-website/ sub-path Pages serves"),
    ):
        if not items:
            continue
        ok = False
        print(f"\n{label}:")
        for path, why in items:
            print(f"  {path}   [{why}]  -- {hint}")

    if not os.path.exists(".nojekyll"):
        ok = False
        print("\n.nojekyll is missing: GitHub Pages will run Jekyll over the tree")

    if ok:
        print("\nOK — every referenced asset exists, is committed, and is relative")
        return 0
    print("\nFAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())