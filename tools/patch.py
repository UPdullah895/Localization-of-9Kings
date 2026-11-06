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
import struct
from pathlib import Path

import UnityPy

import font_merge
import i2

# Path ids move between game versions (0.9.6.5 had I2 12310 / font 923,
# 0.9.8.3 has 14199 / 1073), so objects are found by name and by parsing,
# with the known ids tried first only to keep the installer fast.
I2_FILE, FONT_FILE = "resources.assets", "resources.assets"
I2_HINT, FONT_HINT = 14199, 1073
# Not "ar": I2 applies its runtime RTL fix to any code in its RTL list, and
# "ar-001" (Arabic, world) is not in it. The stored text is already visual.
LANG_NAME, LANG_CODE = "Arabic", "ar-001"

# MonoBehaviour base header: PPtr m_GameObject, bool m_Enabled (aligned), PPtr m_Script.
HEADER_SIZE = 12 + 4 + 12


def _name_of(raw: bytes) -> str:
    """The m_Name string every MonoBehaviour serializes right after its base header."""
    try:
        n = struct.unpack_from("<I", raw, HEADER_SIZE)[0]
        if 0 < n < 200:
            s = raw[HEADER_SIZE + 4:HEADER_SIZE + 4 + n].decode("utf-8")
            if all(32 <= ord(c) < 127 for c in s):
                return s
    except (struct.error, IndexError, UnicodeDecodeError):
        pass
    return ""


def _i2_ok(obj) -> bool:
    try:
        i2.load(obj.get_raw_data())
        return True
    except Exception:
        return False


def find_i2(env):
    """The I2 Localization LanguageSourceAsset, wherever this version put it."""
    if I2_HINT:
        for obj in env.objects:
            if obj.path_id == I2_HINT and obj.assets_file.name == I2_FILE \
                    and obj.type.name == "MonoBehaviour" and _name_of(obj.get_raw_data()) == "I2Languages":
                return obj
    candidates = [o for o in env.objects if o.type.name == "MonoBehaviour"
                  and o.assets_file.name == I2_FILE]
    # Name first (cheap-ish), then a byte-parse for any asset whose name is not
    # readable (no type tree): the I2 asset is the only one that parses as one.
    for obj in candidates:
        if _name_of(obj.get_raw_data()) == "I2Languages" and _i2_ok(obj):
            return obj
    for obj in candidates:
        if _i2_ok(obj):
            return obj
    raise ValueError("no I2 Localization asset in this data.unity3d")


def find_font(env, name: str = "NotoSans-Medium"):
    """The `Font` object with this name (the TTF Arabic glyphs are merged into)."""
    if FONT_HINT:
        for obj in env.objects:
            if obj.path_id == FONT_HINT and obj.type.name == "Font" and obj.assets_file.name == FONT_FILE:
                if obj.read_typetree()["m_Name"] == name:
                    return obj
    for obj in env.objects:
        if obj.type.name == "Font":
            try:
                if obj.read_typetree()["m_Name"] == name:
                    return obj
            except Exception:
                continue
    raise ValueError(f"no Font named {name!r} in this data.unity3d")


def _digests(env) -> dict[tuple[str, int], str]:
    return {(o.assets_file.name, o.path_id): hashlib.sha1(o.get_raw_data()).hexdigest() for o in env.objects}


def english(data_path: Path) -> dict[str, str]:
    env = UnityPy.load(str(data_path))
    src = i2.load(find_i2(env).get_raw_data())
    en = src.lang_index("en")
    return {t.name: t.languages[en] for t in src.terms}


def game_font(data_path: Path) -> bytes:
    env = UnityPy.load(str(data_path))
    return bytes(find_font(env).read_typetree()["m_FontData"])


def patch(data_path: Path, stored: dict[str, str], marks: dict[str, list], arabic_ttf: bytes,
          log=print) -> bytes:
    """Return the patched data.unity3d bytes. `data_path` must be the unmodified game file."""
    env = UnityPy.load(str(data_path))
    before = _digests(env)

    log("Adding the Arabic language...")
    i2_obj = find_i2(env)
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
    font_obj = find_font(env)
    tree = font_obj.read_typetree()
    if tree["m_Name"] != "NotoSans-Medium":
        raise ValueError(f"found {tree['m_Name']!r}, not NotoSans-Medium")
    merged, *_ = font_merge.merge(bytes(tree["m_FontData"]), arabic_ttf)
    final_ttf = font_merge.add_marks(merged, arabic_ttf, marks)
    tree["m_FontData"] = list(final_ttf)
    font_obj.save_typetree(tree)

    log("Writing and verifying...")
    data = env.file.save(packer="original")
    written = UnityPy.load(data)
    after = _digests(written)
    keys = {(i2_obj.assets_file.name, i2_obj.path_id), (font_obj.assets_file.name, font_obj.path_id)}
    if set(before) != set(after):
        raise ValueError("object set changed")
    changed = {k for k in before if before[k] != after[k]}
    if changed != keys:
        raise ValueError(f"unexpected objects changed: {sorted(changed ^ keys)}")
    check = i2.load(find_i2(written).get_raw_data())
    col = check.lang_index(LANG_CODE)
    for name, text in stored.items():
        if check.term(name).languages[col] != text:
            raise ValueError(f"{name}: written text did not read back")
    if bytes(find_font(written).read_typetree()["m_FontData"]) != final_ttf:
        raise ValueError("font data did not read back")
    return data
