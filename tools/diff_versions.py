"""Diff the game's I2 terms between two data.unity3d builds and the translations.

Usage: diff_versions.py OLD_DATA NEW_DATA

Prints: added terms, removed terms, terms whose English changed, and which of the
current terms still have no Arabic translation.
"""
import json
import sys
from pathlib import Path

import UnityPy

import i2

ROOT = Path(__file__).resolve().parent.parent
AR = json.loads((ROOT / "translations/ar.json").read_text(encoding="utf-8"))
HEADER = 12 + 4 + 12


def english(path: Path) -> dict[str, str]:
    env = UnityPy.load(str(path))
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        raw = obj.get_raw_data()
        if raw[HEADER + 4:HEADER + 5] != b"I":
            continue
        try:
            src = i2.load(raw)
        except Exception:
            continue
        en = src.lang_index("en")
        return {t.name: t.languages[en] for t in src.terms}
    raise SystemExit(f"no I2 asset found in {path}")


old = english(Path(sys.argv[1]))
new = english(Path(sys.argv[2]))
out = ROOT / "work"
out.mkdir(exist_ok=True)
(out / "en_old.json").write_text(json.dumps(old, ensure_ascii=False, indent=1), encoding="utf-8")
(out / "en.json").write_text(json.dumps(new, ensure_ascii=False, indent=1), encoding="utf-8")

added = [k for k in new if k not in old]
removed = [k for k in old if k not in new]
changed = [k for k in new if k in old and new[k] != old[k]]
missing = [k for k in new if k not in AR and not k.startswith("Format_")]

print(f"old terms: {len(old)}   new terms: {len(new)}")
print(f"added {len(added)}, removed {len(removed)}, changed text {len(changed)}, missing translations {len(missing)}")

print("\n== ADDED ==")
for k in added:
    print(json.dumps({k: new[k]}, ensure_ascii=False))
print("\n== REMOVED ==")
for k in removed:
    print(k, "|", json.dumps(AR.get(k, ""), ensure_ascii=False))
print("\n== CHANGED ENGLISH ==")
for k in changed:
    print(k)
    print("   old:", json.dumps(old[k], ensure_ascii=False))
    print("   new:", json.dumps(new[k], ensure_ascii=False))
    print("   ar :", json.dumps(AR.get(k, None), ensure_ascii=False))
print("\n== MISSING ARABIC ==")
for k in missing:
    print(json.dumps({k: new[k]}, ensure_ascii=False))
