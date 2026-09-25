"""Build a patched data.unity3d that adds Arabic as a new I2 Localization language.

Input:  original/data.unity3d (pristine, read-only) + translations/ar.json
Output: build/data.unity3d

Arabic text is stored in normal logical order, unshaped. I2 Localization applies
its own Arabic shaping and right-to-left fix when the current language is RTL,
so pre-shaping here would shape the text twice.

After saving, the output is re-opened and checked: the Arabic column must be
present and every other object in the file must be byte-identical to the
original. Any difference aborts the build.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import UnityPy

import i2

ROOT = Path(__file__).resolve().parent.parent
ORIGINAL = ROOT / "original/data.unity3d"
TRANSLATIONS = ROOT / "translations/ar.json"
OUT = ROOT / "build/data.unity3d"

I2_FILE, I2_PATH_ID = "resources.assets", 12310
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


def main() -> None:
    translations = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))

    env = UnityPy.load(str(ORIGINAL))
    before = object_digests(env)
    obj = find(env, I2_FILE, I2_PATH_ID)
    obj.set_raw_data(patch_i2(obj.get_raw_data(), translations))

    OUT.parent.mkdir(exist_ok=True)
    OUT.write_bytes(env.file.save(packer="original"))

    # Verify the file we actually wrote, not the in-memory environment.
    check = UnityPy.load(str(OUT))
    after = object_digests(check)
    key = (I2_FILE, I2_PATH_ID)
    if set(before) != set(after):
        raise SystemExit("object set changed")
    changed = [k for k in before if before[k] != after[k]]
    if changed != [key]:
        raise SystemExit(f"unexpected objects changed: {changed}")
    src = i2.load(find(check, *key).get_raw_data())
    col = src.lang_index(LANG_CODE)
    for name, text in translations.items():
        if src.term(name).languages[col] != text:
            raise SystemExit(f"{name}: written text did not read back")

    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size} bytes)")
    print(f"languages: {len(src.languages)} (Arabic at index {col}); "
          f"{len(translations)} terms translated, {len(src.terms) - len(translations)} fall back to English")
    print(f"verified: only {key} changed; all {len(before) - 1} other objects byte-identical")


if __name__ == "__main__":
    sys.exit(main())
