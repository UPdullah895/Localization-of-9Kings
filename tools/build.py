"""Build a patched data.unity3d that adds Arabic to 9 Kings.

Input:  original/data.unity3d (pristine, read-only), translations/ar.json,
        fonts/NotoSansArabic-Medium.ttf
Output: build/data.unity3d

Two objects change:
- I2Languages gets an Arabic column (see i2.py).
- The NotoSans-Medium `Font` gets Arabic glyphs merged in (see font_merge.py).
  Arabic falls back to the NotoSans TMP assets, which rasterize from this TTF.

Translations are written in normal logical order (translations/ar.json) and
stored in the asset in visual order, shaped and wrapped (see visual.py). The
language code is one I2 does not treat as right-to-left, so I2's own runtime
RTL fix, which garbles this game's text, never runs. Harakat become glyphs
added to the merged font, so the font is finished only after all text is made.

After saving, the output is re-opened and checked: the Arabic column must be
present, the font must carry the merged TTF, and every other object in the
file must be byte-identical to the original. Any difference aborts the build.
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

import UnityPy

import check_translations
import font_merge
import i2
import visual

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "original/data.unity3d"
TRANSLATIONS = ROOT / "translations/ar.json"
LAYOUT = ROOT / "translations/layout.json"
ARABIC_FONT = ROOT / "fonts/NotoSansArabic-Medium.ttf"
OUT = ROOT / "build/data.unity3d"

I2_FILE, I2_PATH_ID = "resources.assets", 12310
FONT_FILE, FONT_PATH_ID = "resources.assets", 923     # Font "NotoSans-Medium"
# Not "ar": I2 applies its RTL fix to any code in its RTL list, and "ar-001"
# (Arabic, world) is not in it.
LANG_NAME, LANG_CODE = "Arabic", "ar-001"


def find(env, file_name: str, path_id: int):
    return next(o for o in env.objects if o.assets_file.name == file_name and o.path_id == path_id)


def check(english: dict[str, str], translations: dict[str, str]) -> None:
    errors, _ = check_translations.check(english, translations)
    if errors:
        raise SystemExit("translation errors (run tools/check_translations.py):\n  " + "\n  ".join(errors))


def make_visual(translations: dict[str, str], merged: TTFont) -> tuple[dict[str, str], visual.MarkGlyphs]:
    widths = json.loads(LAYOUT.read_text(encoding="utf-8"))["widths"]
    marks = visual.MarkGlyphs(TTFont(ARABIC_FONT), merged)
    metrics = visual.Metrics(merged)
    out = {}
    for name, text in translations.items():
        max_em = next((w for pattern, w in widths.items() if re.search(pattern, name)), None)
        try:
            out[name] = visual.visual(text, marks, metrics, max_em)
        except ValueError as e:
            raise SystemExit(f"{name}: {e}")
    return out, marks


def patch_i2(raw: bytes, stored: dict[str, str]) -> bytes:
    src = i2.load(raw)
    col = src.add_language(LANG_NAME, LANG_CODE, fill_from="en")
    for t in src.terms:
        if t.name in stored:
            t.languages[col] = stored[t.name]
    return i2.serialize(src)


def object_digests(env) -> dict[tuple[str, int], str]:
    return {(o.assets_file.name, o.path_id): hashlib.sha1(o.get_raw_data()).hexdigest() for o in env.objects}


def finish_font(merged_ttf: bytes, marks: visual.MarkGlyphs, merged: TTFont) -> bytes:
    before = merged.getBestCmap().copy()
    marks.add_to(merged)
    out = io.BytesIO()
    merged.save(out)
    data = out.getvalue()
    cmap = TTFont(io.BytesIO(data)).getBestCmap()
    if any(cmap.get(cp) != g for cp, g in before.items()):
        raise SystemExit("adding mark glyphs changed an existing cmap entry")
    for pua, _ in marks.glyphs.values():
        if ord(pua) not in cmap:
            raise SystemExit(f"mark glyph U+{ord(pua):04X} missing from the font")
    return data


def set_font(obj, data: bytes) -> None:
    tree = obj.read_typetree()
    tree["m_FontData"] = list(data)
    obj.save_typetree(tree)


def main() -> None:
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))

    env = UnityPy.load(str(ORIGINAL))
    before = object_digests(env)
    i2_obj, font_obj = find(env, I2_FILE, I2_PATH_ID), find(env, FONT_FILE, FONT_PATH_ID)
    source = i2.load(i2_obj.get_raw_data())
    en = source.lang_index("en")
    check({t.name: t.languages[en] for t in source.terms}, translations)

    font_tree = font_obj.read_typetree()
    if font_tree["m_Name"] != "NotoSans-Medium":
        raise SystemExit(f"path_id {FONT_PATH_ID} is {font_tree['m_Name']!r}, not NotoSans-Medium")
    merged_ttf, kept, added, shifted = font_merge.merge(bytes(font_tree["m_FontData"]), ARABIC_FONT.read_bytes())
    merged = TTFont(io.BytesIO(merged_ttf))
    stored, marks = make_visual(translations, merged)
    final_ttf = finish_font(merged_ttf, marks, merged)

    i2_obj.set_raw_data(patch_i2(i2_obj.get_raw_data(), stored))
    set_font(font_obj, final_ttf)

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(env.file.save(packer="original"))

    # Verify the file we actually wrote, not the in-memory environment.
    written = UnityPy.load(str(OUT))
    after = object_digests(written)
    i2_key, font_key = (I2_FILE, I2_PATH_ID), (FONT_FILE, FONT_PATH_ID)
    if set(before) != set(after):
        raise SystemExit("object set changed")
    changed = sorted(k for k in before if before[k] != after[k])
    if changed != sorted([i2_key, font_key]):
        raise SystemExit(f"unexpected objects changed: {changed}")
    src = i2.load(find(written, *i2_key).get_raw_data())
    col = src.lang_index(LANG_CODE)
    for name, text in stored.items():
        if src.term(name).languages[col] != text:
            raise SystemExit(f"{name}: written text did not read back")
    if bytes(find(written, *font_key).read_typetree()["m_FontData"]) != final_ttf:
        raise SystemExit("font data did not read back")

    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    print(f"languages: {len(src.languages)} (Arabic at index {col}); "
          f"{len(translations)} terms translated, {len(src.terms) - len(translations)} fall back to English")
    print(f"font: {kept} original codepoints unchanged, {added} Arabic codepoints added, "
          f"{shifted} overhanging forms given left clearance, {len(marks.glyphs)} harakat glyphs")
    print(f"verified: only I2Languages and NotoSans-Medium changed; "
          f"all {len(before) - 2} other objects byte-identical")

if __name__ == "__main__":
    sys.exit(main())
