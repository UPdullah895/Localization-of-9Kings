"""Check an installed data.unity3d really carries the Arabic column (read-only).

    verify_install.py [GAME_DIR]

Reads the game's live file: the language column, the stored strings (a few
spot checks plus the overall count), and the Arabic codepoints in the font.
"""
import sys
from pathlib import Path

import UnityPy
from fontTools.ttLib import TTFont
import io

sys.path.insert(0, str(Path(__file__).resolve().parent))
import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "installer"))
import steam  # noqa: E402


def main() -> int:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else steam.find_game()[0]
    data = folder / "9Kings_Data/data.unity3d"
    env = UnityPy.load(str(data))
    src = patch.i2.load(patch.find_i2(env).get_raw_data())
    col = src.lang_index("ar-001")
    lang = next(l for l in src.languages if l.code == "ar-001")
    filled = [t.name for t in src.terms if t.languages[col].strip()]
    print(f"file        : {data}")
    print(f"language    : {lang.name} ({lang.code}) at index {col} of {len(src.languages)}")
    print(f"terms       : {len(src.terms)} total, {len(filled)} with Arabic text")

    for name in ("Building_Factory", "Troop_Leech", "Spell_Singularity", "UI_NewRecord",
                 "Challenge_Joker1", "MainMenu_Main_RankedMode", "Building_Amplifier_Desc"):
        try:
            print(f"  {name:26s} -> {src.term(name).languages[col]!r}")
        except StopIteration:
            print(f"  {name:26s} -> (not in this build)")

    font = TTFont(io.BytesIO(bytes(patch.find_font(env).read_typetree()["m_FontData"])))
    cmap = font.getBestCmap()
    arabic = [c for c in cmap if 0x0600 <= c <= 0x06FF]
    forms = [c for c in cmap if 0xFE70 <= c <= 0xFEFC]
    print(f"font        : {len(cmap)} codepoints, {len(arabic)} Arabic letters, {len(forms)} presentation forms")

    # The six Format_* terms are number formats, so they keep the English text.
    formats = [t for t in src.terms if t.name.startswith("Format_")]
    en = src.lang_index("en")
    formats_ok = all(t.languages[col] == t.languages[en] for t in formats)
    translated = sum(1 for t in src.terms if not t.name.startswith("Format_"))
    ok = formats_ok and translated == 2070 and arabic and forms
    print("OK" if ok else "PROBLEM")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
