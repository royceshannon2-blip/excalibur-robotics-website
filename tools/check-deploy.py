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


def css_rules(css: str) -> list[tuple[str, str, int]]:
    """(selector, body, offset) for every style rule, descending into @media.

    Comments are stripped first: several of them mention `.in { opacity: 1 }`
    in prose, and a brace inside a comment would derail a naive scan.
    """
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    rules: list[tuple[str, str, int]] = []
    stack: list[tuple[str, int]] = []
    prelude_start = 0
    for i, ch in enumerate(css):
        if ch == "{":
            stack.append((css[prelude_start:i].strip(), i))
            prelude_start = i + 1
        elif ch == "}":
            if stack:
                prelude, open_at = stack.pop()
                body = css[open_at + 1:i]
                if prelude.startswith("@"):
                    if "{" in body:  # nested (e.g. @media)
                        rules.extend(css_rules(body))
                elif prelude:
                    rules.append((prelude, body, open_at))
            prelude_start = i + 1
    return rules


def check_reveal_order(html: str) -> list[str]:
    """Reveal targets must not be hidden by a rule that comes after `.in`.

    This is not hypothetical: the reveal's hidden state was split across two
    style blocks, so `.in { opacity: 1 }` sat ABOVE `.alumni-card { opacity: 0 }`,
    tied on specificity, and lost on source order. The .in class was applied
    and did nothing, and 21 elements — the machine figure, the robot awards,
    the donate panel, every fund card, every alumni card, every tier and both
    sponsor slots — were invisible on the page with no error to point at it.
    """
    m = re.search(r"var targets\s*=\s*document\.querySelectorAll\(\s*['\"]([^'\"]+)['\"]", html)
    if not m:
        return ["could not find the reveal target list in the page's script"]
    targets = {t.strip() for t in m.group(1).split(",") if t.strip()}

    style = "\n".join(
        b for b in re.findall(r"<style>(.*?)</style>", html, re.S) if "inlineCSS" not in b
    )
    rules = css_rules(style)

    in_offset = None
    for selector, body, offset in rules:
        if ".in" in {s.strip() for s in selector.split(",")} and "opacity" in body:
            in_offset = offset
            break
    if in_offset is None:
        return ["no `.in { opacity: ... }` rule found — the reveal has no visible state"]

    problems = []
    for selector, body, offset in rules:
        if offset <= in_offset:
            continue
        if not re.search(r"opacity\s*:\s*0(?![.\d])", body):
            continue
        hit = sorted(targets & {s.strip() for s in selector.split(",")})
        for t in hit:
            problems.append(
                f"{t}   [hidden after .in]  -- this rule outranks `.in` on source order, "
                f"so the element never becomes visible"
            )
    return problems


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

    reveal = check_reveal_order(html)
    if reveal:
        ok = False
        print("\nREVEAL ORDER:")
        for line in reveal:
            print(f"  {line}")

    if ok:
        print("\nOK — every referenced asset exists, is committed, and is relative")
        return 0
    print("\nFAILED")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())