"""Dump the Unity Localization shared keys and per-locale strings (bundles carry type trees).

Writes work/tables.json: {table: {entry_id: {"key": ..., "<locale>": text, ...}}}
"""
import json, glob, os, sys
import UnityPy
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
B = ROOT / "original/aa/StandaloneWindows64"

tables = {}
env = UnityPy.load(str(B / "localization-assets-shared_assets_all.bundle"))
for obj in env.objects:
    if obj.type.name != "MonoBehaviour":
        continue
    t = obj.read_typetree()
    if "m_Entries" not in t:
        continue
    name = t["m_Name"].replace(" Shared Data", "")
    tables[name] = {str(e["m_Id"]): {"key": e["m_Key"]} for e in t["m_Entries"]}

for path in sorted(B.glob("localization-string-tables-*.bundle")):
    env = UnityPy.load(str(path))
    for obj in env.objects:
        if obj.type.name != "MonoBehaviour":
            continue
        t = obj.read_typetree()
        if "m_TableData" not in t:
            continue
        table, loc = t["m_Name"].rsplit("_", 1)
        for e in t["m_TableData"]:
            tables.setdefault(table, {}).setdefault(str(e["m_Id"]), {"key": None})[loc] = e["m_Localized"]

(ROOT / "work").mkdir(exist_ok=True)
(ROOT / "work/tables.json").write_text(json.dumps(tables, ensure_ascii=False, indent=1))
for name, entries in tables.items():
    print(f"{name}: {len(entries)} entries")
