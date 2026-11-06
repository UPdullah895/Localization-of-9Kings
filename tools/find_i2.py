"""Find named MonoBehaviours (no type tree needed) and identify the I2 asset.

Reads the m_Name string that every MonoBehaviour serializes right after its
12-byte base header, then tries i2.load() on the candidate so the I2 asset is
identified by its bytes, not by a path_id that game updates move around.
"""
import struct
import sys
from pathlib import Path

import UnityPy

import i2

ROOT = Path(__file__).resolve().parent.parent
env = UnityPy.load(str(ROOT / "original/data.unity3d"))
HEADER = 12 + 4 + 12


def name_of(raw: bytes) -> str:
    try:
        n = struct.unpack_from("<I", raw, HEADER)[0]
        if 0 < n < 200:
            s = raw[HEADER + 4:HEADER + 4 + n].decode("utf-8")
            if all(32 <= ord(c) < 127 for c in s):
                return s
    except Exception:
        pass
    return ""


want = {"I2Languages", "LocalizationFonts"}
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    raw = obj.get_raw_data()
    nm = name_of(raw)
    if nm in want:
        print(f"{nm}: {obj.assets_file.name} path_id={obj.path_id} {len(raw)} bytes")
        if nm == "I2Languages":
            try:
                src = i2.load(raw)
                langs = [(l.name, l.code) for l in src.languages]
                print(f"  parsed OK: {len(src.terms)} terms, {len(src.languages)} languages")
                print(f"  languages: {langs}")
            except Exception as e:
                print("  i2.load failed:", e)
