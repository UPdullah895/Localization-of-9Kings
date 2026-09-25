"""Build the Arabic translation: installer payload plus a patched data.unity3d.

Input:  original/data.unity3d (pristine, read-only), translations/ar.json,
        translations/layout.json, fonts/NotoSansArabic-Medium.ttf
Output: installer/payload/{strings,marks,manifest}.json  (committed; the installer's data)
        build/data.unity3d                                (for tools/deploy.py)

Translations are written in normal logical order and stored in visual order,
shaped and wrapped (visual.py); harakat become glyphs added to the merged font.
The patch itself (patch.py) is the same code the installer runs, and the
manifest records the hashes of the original and patched file, so the installer
can recognise the supported game version and verify its own result.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

import check_translations
import font_merge
import patch
import visual

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "original/data.unity3d"
TRANSLATIONS = ROOT / "translations/ar.json"
LAYOUT = ROOT / "translations/layout.json"
ARABIC_FONT = ROOT / "fonts/NotoSansArabic-Medium.ttf"
PAYLOAD = ROOT / "installer/payload"
OUT = ROOT / "build/data.unity3d"

# The game version original/ was copied from (Application.version, Steam build id).
GAME_VERSION, STEAM_BUILD = "0.9.6.5", "25462185"

# Labels the game completes by appending a value in code ("Health: " + "50"). The
# value always lands on the right, so the label is laid out left-to-right as a unit,
# "الصحة: 50", instead of RTL, where the number would end up glued to the word.
APPENDED_VALUE_LABEL = re.compile(r"^TerrainPopup_")


def make_visual(translations: dict[str, str], merged: TTFont) -> tuple[dict[str, str], visual.MarkGlyphs]:
    widths = json.loads(LAYOUT.read_text(encoding="utf-8"))["widths"]
    marks = visual.MarkGlyphs(TTFont(ARABIC_FONT), merged)
    metrics = visual.Metrics(merged)
    out = {}
    for name, text in translations.items():
        max_em = next((w for pattern, w in widths.items() if re.search(pattern, name)), None)
        try:
            label = APPENDED_VALUE_LABEL.search(name) and re.fullmatch(r"([^{}]*?)(:\s*)", text)
            if label:
                out[name] = visual.visual(label.group(1), marks, metrics) + label.group(2)
            else:
                out[name] = visual.visual(text, marks, metrics, max_em)
        except ValueError as e:
            raise SystemExit(f"{name}: {e}")
    return out, marks


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    errors, _ = check_translations.check(patch.english(ORIGINAL), translations)
    if errors:
        raise SystemExit("translation errors (run tools/check_translations.py):\n  " + "\n  ".join(errors))

    arabic_ttf = ARABIC_FONT.read_bytes()
    merged_ttf, kept, added, shifted = font_merge.merge(patch.game_font(ORIGINAL), arabic_ttf)
    stored, marks = make_visual(translations, TTFont(io.BytesIO(merged_ttf)))

    data = patch.patch(ORIGINAL, stored, marks.spec(), arabic_ttf)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(data)

    original = ORIGINAL.read_bytes()
    PAYLOAD.mkdir(parents=True, exist_ok=True)
    write_json(PAYLOAD / "strings.json", stored)
    write_json(PAYLOAD / "marks.json", marks.spec())
    write_json(PAYLOAD / "manifest.json", {
        "game_version": GAME_VERSION,
        "steam_build": STEAM_BUILD,
        "original_sha256": sha256(original),
        "original_size": len(original),
        "patched_sha256": sha256(data),
        "terms_translated": len(stored),
    })

    print(f"wrote {OUT.relative_to(ROOT)} ({len(data)} bytes) and {PAYLOAD.relative_to(ROOT)}/")
    print(f"{len(stored)} terms translated")
    print(f"font: {kept} original codepoints unchanged, {added} Arabic codepoints added, "
          f"{shifted} overhanging forms given left clearance, {len(marks.glyphs)} harakat glyphs")
    print("verified: only I2Languages and NotoSans-Medium changed, both read back exactly")


if __name__ == "__main__":
    sys.exit(main())
