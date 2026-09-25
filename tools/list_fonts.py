"""List Font objects and font-related MonoBehaviours (TMP font assets, TMP Settings) by name."""
import struct
from pathlib import Path
import UnityPy
ROOT = Path(__file__).resolve().parent.parent
env = UnityPy.load(str(ROOT / "original/data.unity3d"))

def mb_name(raw):
    n = struct.unpack_from("<I", raw, 28)[0]
    return raw[32:32 + n].decode("utf-8", "replace") if n < 200 else "?"

for obj in env.objects:
    t = obj.type.name
    if t == "Font":
        f = obj.read()
        data = getattr(f, "m_FontData", None) or []
        print(f"Font      {obj.assets_file.name:22s} pid={obj.path_id:<8d} {f.m_Name!r} ttf_bytes={len(data)}")
    elif t == "MonoBehaviour":
        raw = obj.get_raw_data()
        name = mb_name(raw)
        if any(k in name for k in ("SDF", "Noto", "TauSans", "TMP Settings", "Font")):
            print(f"MB        {obj.assets_file.name:22s} pid={obj.path_id:<8d} {name!r} size={len(raw)}")
