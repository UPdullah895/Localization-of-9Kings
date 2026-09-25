"""Build a patched data.unity3d that adds Arabic to 9 Kings.

Input:  original/data.unity3d (pristine, read-only), translations/ar.json,
        fonts/NotoSansArabic-Medium.ttf
Output: build/data.unity3d

Two objects change:
- I2Languages gets an Arabic column (see i2.py).
- The NotoSans-Medium `Font` gets Arabic glyphs merged in (see font_merge.py).
  Arabic falls back to the NotoSans TMP assets, which rasterize from this TTF.

Arabic text is stored in normal logical order, unshaped. I2 Localization applies
its own Arabic shaping and right-to-left fix when the current language is RTL,
so pre-shaping here would shape the text twice.

After saving, the output is re-opened and checked: the Arabic column must be
present, the font must carry the merged TTF, and every other object in the
file must be byte-identical to the original. Any difference aborts the build.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import UnityPy

import font_merge
import i2

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "original/data.unity3d"
TRANSLATIONS = ROOT / "translations/ar.json"
ARABIC_FONT = ROOT / "fonts/NotoSansArabic-Medium.ttf"
OUT = ROOT / "build/data.unity3d"

I2_FILE, I2_PATH_ID = "resources.assets", 12310
FONT_FILE, FONT_PATH_ID = "resources.assets", 923     # Font "NotoSans-Medium"
LANG_NAME, LANG_CODE = "Arabic", "ar"


def find(env, file_name: str, path_id: int):
    return next(o for o in env.objects if o.assets_file.name == file_name and o.path_id == path_id)


def patch_i2(raw: bytes, translations: dict[str, str]) -> bytes:
    src = i2.load(raw)
    names = {t.name for t in src.terms}
    unknown = sorted(set(translations) - names)
    if unknown:
        raise SystemExit(f"translations/ar.json has terms the game doesn't: {unknown}")
    col = src.add_language(LANG_NAME, LANG_CODE, fill_from="en")
    for t in src.terms:
        if t.name in translations:
            t.languages[col] = translations[t.name]
    return i2.serialize(src)


def object_digests(env) -> dict[tuple[str, int], str]:
    return {(o.assets_file.name, o.path_id): hashlib.sha1(o.get_raw_data()).hexdigest() for o in env.objects}


def patch_font(obj) -> tuple[bytes, int, int, int]:
    tree = obj.read_typetree()
    if tree["m_Name"] != "NotoSans-Medium":
        raise SystemExit(f"path_id {FONT_PATH_ID} is {tree['m_Name']!r}, not NotoSans-Medium")
    merged, kept, added, shifted = font_merge.merge(bytes(tree["m_FontData"]), ARABIC_FONT.read_bytes())
    tree["m_FontData"] = list(merged)
    obj.save_typetree(tree)
    return merged, kept, added, shifted


def main() -> None:
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))

    env = UnityPy.load(str(ORIGINAL))
    before = object_digests(env)
    obj = find(env, I2_FILE, I2_PATH_ID)
    obj.set_raw_data(patch_i2(obj.get_raw_data(), translations))
    merged_ttf, kept, added, shifted = patch_font(find(env, FONT_FILE, FONT_PATH_ID))

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(env.file.save(packer="original"))

    # Verify the file we actually wrote, not the in-memory environment.
    check = UnityPy.load(str(OUT))
    after = object_digests(check)
    i2_key, font_key = (I2_FILE, I2_PATH_ID), (FONT_FILE, FONT_PATH_ID)
    if set(before) != set(after):
        raise SystemExit("object set changed")
    changed = sorted(k for k in before if before[k] != after[k])
    if changed != sorted([i2_key, font_key]):
        raise SystemExit(f"unexpected objects changed: {changed}")
    src = i2.load(find(check, *i2_key).get_raw_data())
    col = src.lang_index(LANG_CODE)
    for name, text in translations.items():
        if src.term(name).languages[col] != text:
            raise SystemExit(f"{name}: written text did not read back")
    if bytes(find(check, *font_key).read_typetree()["m_FontData"]) != merged_ttf:
        raise SystemExit("font data did not read back")

    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    print(f"languages: {len(src.languages)} (Arabic at index {col}); "
          f"{len(translations)} terms translated, {len(src.terms) - len(translations)} fall back to English")
    print(f"font: {kept} original codepoints unchanged, {added} Arabic codepoints added, "
          f"{shifted} overhanging forms given left clearance")
    print(f"verified: only I2Languages and NotoSans-Medium changed; "
          f"all {len(before) - 2} other objects byte-identical")

if __name__ == "__main__":
    sys.exit(main())
