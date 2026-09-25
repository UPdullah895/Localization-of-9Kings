"""Search every decompressed serialized file in data.unity3d, plus IL2CPP metadata, for needles.

Usage: find_strings.py NEEDLE [NEEDLE ...]   (UTF-8; also tries UTF-16LE)
"""
import sys
from pathlib import Path
import UnityPy
ROOT = Path(__file__).resolve().parent.parent
needles = sys.argv[1:]

blobs = {"global-metadata.dat": (ROOT / "original/il2cpp/global-metadata.dat").read_bytes()}
env = UnityPy.load(str(ROOT / "original/data.unity3d"))
for bundle in env.files.values():
    for name, f in getattr(bundle, "files", {}).items():
        reader = getattr(f, "reader", f)
        try:
            blobs[name] = bytes(reader.bytes)
        except Exception:
            try:
                blobs[name] = bytes(f.bytes)
            except Exception as e:
                print("skip", name, e)

for n in needles:
    for enc in ("utf-8", "utf-16-le"):
        b = n.encode(enc)
        hits = {name: blob.count(b) for name, blob in blobs.items() if b in blob}
        if hits:
            print(f"{n!r} [{enc}]: {hits}")
