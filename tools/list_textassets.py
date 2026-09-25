"""List TextAssets in data.unity3d with size and a preview (read-only)."""
from pathlib import Path
import UnityPy
ROOT = Path(__file__).resolve().parent.parent
env = UnityPy.load(str(ROOT / "original/data.unity3d"))
for obj in env.objects:
    if obj.type.name != "TextAsset":
        continue
    ta = obj.read()
    raw = ta.m_Script.encode("utf-8", "surrogateescape") if isinstance(ta.m_Script, str) else bytes(ta.m_Script)
    head = raw[:90].decode("utf-8", "replace").replace("\n", "\\n")
    print(f"{len(raw):9d}  {obj.assets_file.name:22s} {ta.m_Name!r:40s} {head}")
