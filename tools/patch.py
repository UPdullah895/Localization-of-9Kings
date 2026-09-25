"""Apply the Arabic translation to the game's data.unity3d.

Shared by build.py (developer build) and the installer (player's own game
files), so an installed game is byte-identical to the build verified here.
Nothing from the game is shipped: the inputs are the player's data.unity3d,
the translated strings (already in visual form, see visual.py), the harakat
glyph spec, and Noto Sans Arabic (OFL).

Two objects change:
- I2Languages gets an Arabic column.
- The NotoSans-Medium `Font` gets Arabic glyphs merged in (font_merge.py).
  Arabic falls back to the NotoSans TMP assets, which rasterize from this TTF.

The result is re-read from the saved bytes and checked: every other object
must be byte-identical and both changed objects must read back exactly.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import UnityPy

import font_merge
import i2

I2_FILE, I2_PATH_ID = "resources.assets", 12310
FONT_FILE, FONT_PATH_ID = "resources.assets", 923     # Font "NotoSans-Medium"
# Not "ar": I2 applies its runtime RTL fix to any code in its RTL list, and
# "ar-001" (Arabic, world) is not in it. The stored text is already visual.
LANG_NAME, LANG_CODE = "Arabic", "ar-001"


def _find(env, file_name: str, path_id: int):
    return next(o for o in env.objects if o.assets_file.name == file_name and o.path_id == path_id)


def _digests(env) -> dict[tuple[str, int], str]:
    return {(o.assets_file.name, o.path_id): hashlib.sha1(o.get_raw_data()).hexdigest() for o in env.objects}


def english(data_path: Path) -> dict[str, str]:
    env = UnityPy.load(str(data_path))
    src = i2.load(_find(env, I2_FILE, I2_PATH_ID).get_raw_data())
    en = src.lang_index("en")
    return {t.name: t.languages[en] for t in src.terms}


def game_font(data_path: Path) -> bytes:
    env = UnityPy.load(str(data_path))
    tree = _find(env, FONT_FILE, FONT_PATH_ID).read_typetree()
    if tree["m_Name"] != "NotoSans-Medium":
        raise ValueError(f"path_id {FONT_PATH_ID} is {tree['m_Name']!r}, not NotoSans-Medium")
    return bytes(tree["m_FontData"])


def patch(data_path: Path, stored: dict[str, str], marks: dict[str, list], arabic_ttf: bytes,
          log=print) -> bytes:
    """Return the patched data.unity3d bytes. `data_path` must be the unmodified game file."""
    env = UnityPy.load(str(data_path))
    before = _digests(env)

    log("Adding the Arabic language...")
    i2_obj = _find(env, I2_FILE, I2_PATH_ID)
    src = i2.load(i2_obj.get_raw_data())
    if any(l.name == LANG_NAME for l in src.languages):
        raise ValueError("this data.unity3d already has an Arabic column")
    col = src.add_language(LANG_NAME, LANG_CODE, fill_from="en")
    for t in src.terms:
        if t.name in stored:
            t.languages[col] = stored[t.name]
    missing = set(stored) - {t.name for t in src.terms}
    if missing:
        raise ValueError(f"terms not in this game version: {sorted(missing)[:5]}")
    i2_obj.set_raw_data(i2.serialize(src))

    log("Adding Arabic letters to the game font...")
    font_obj = _find(env, FONT_FILE, FONT_PATH_ID)
    tree = font_obj.read_typetree()
    if tree["m_Name"] != "NotoSans-Medium":
        raise ValueError(f"path_id {FONT_PATH_ID} is {tree['m_Name']!r}, not NotoSans-Medium")
    merged, *_ = font_merge.merge(bytes(tree["m_FontData"]), arabic_ttf)
    final_ttf = font_merge.add_marks(merged, arabic_ttf, marks)
    tree["m_FontData"] = list(final_ttf)
    font_obj.save_typetree(tree)

    log("Writing and verifying...")
    data = env.file.save(packer="original")
    written = UnityPy.load(data)
    after = _digests(written)
    keys = {(I2_FILE, I2_PATH_ID), (FONT_FILE, FONT_PATH_ID)}
    if set(before) != set(after):
        raise ValueError("object set changed")
    changed = {k for k in before if before[k] != after[k]}
    if changed != keys:
        raise ValueError(f"unexpected objects changed: {sorted(changed ^ keys)}")
    check = i2.load(_find(written, I2_FILE, I2_PATH_ID).get_raw_data())
    col = check.lang_index(LANG_CODE)
    for name, text in stored.items():
        if check.term(name).languages[col] != text:
            raise ValueError(f"{name}: written text did not read back")
    if bytes(_find(written, FONT_FILE, FONT_PATH_ID).read_typetree()["m_FontData"]) != final_ttf:
        raise ValueError("font data did not read back")
    return data
