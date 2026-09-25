"""Validate translations/ar.json against the game's English text.

Errors (the build refuses to proceed):
- a term the game doesn't have
- a translated `Format_*` term (these are .NET number formats, not text)
- placeholders ({VAR1}, {KING}, ...) differ from the English, as a multiset
- rich-text tags differ from the English (same tags, same count), or are unbalanced

Warnings:
- a different number of line breaks than the English (often intended)

Usage: check_translations.py   (reads the English from original/data.unity3d)
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER = re.compile(r"\{[A-Za-z0-9_]+\}")
TAG = re.compile(r"</?[a-zA-Z]+(?:=[^>]*)?>")


def _tag_names(s: str) -> collections.Counter:
    # Compare opening tags by full text (<color=#{KINGCOLOR}>) and closings by name.
    return collections.Counter(TAG.findall(s))


def _balanced(s: str) -> bool:
    stack = []
    for t in TAG.findall(s):
        name = re.match(r"</?([a-zA-Z]+)", t).group(1)
        if t.startswith("</"):
            if not stack or stack.pop() != name:
                return False
        else:
            stack.append(name)
    return not stack


def check(english: dict[str, str], arabic: dict[str, str]) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    for term, ar in arabic.items():
        if term not in english:
            errors.append(f"{term}: not a game term")
            continue
        en = english[term]
        if term.startswith("Format_"):
            errors.append(f"{term}: number format, must not be translated")
            continue
        if collections.Counter(PLACEHOLDER.findall(en)) != collections.Counter(PLACEHOLDER.findall(ar)):
            errors.append(f"{term}: placeholders {sorted(PLACEHOLDER.findall(en))} -> {sorted(PLACEHOLDER.findall(ar))}")
        if _tag_names(en) != _tag_names(ar):
            errors.append(f"{term}: tags differ from English")
        elif not _balanced(ar):
            errors.append(f"{term}: unbalanced tags")
        if en.count("\n") != ar.count("\n"):
            warnings.append(f"{term}: {en.count(chr(10))} line breaks in English, {ar.count(chr(10))} in Arabic")
    return errors, warnings


def english_terms() -> dict[str, str]:
    import UnityPy
    import i2
    env = UnityPy.load(str(ROOT / "original/data.unity3d"))
    obj = next(o for o in env.objects if o.assets_file.name == "resources.assets" and o.path_id == 12310)
    src = i2.load(obj.get_raw_data())
    en = src.lang_index("en")
    return {t.name: t.languages[en] for t in src.terms}


def main() -> int:
    arabic = json.loads((ROOT / "translations/ar.json").read_text(encoding="utf-8"))
    english = english_terms()
    errors, warnings = check(english, arabic)
    for w in warnings:
        print("warning:", w)
    for e in errors:
        print("ERROR:", e)
    print(f"{len(arabic)}/{len(english)} terms translated, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
