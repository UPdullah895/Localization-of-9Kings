"""Extract the raw serialized bytes of the I2Languages MonoBehaviour (no type tree available)."""
from pathlib import Path
import UnityPy
ROOT = Path(__file__).resolve().parent.parent
env = UnityPy.load(str(ROOT / "original/data.unity3d"))
for obj in env.objects:
    if obj.type.name == "MonoBehaviour" and obj.assets_file.name == "resources.assets":
        raw = obj.get_raw_data()
        if b"I2Languages" in raw[:200]:
            (ROOT / "work/I2Languages.raw").write_bytes(raw)
            print("path_id", obj.path_id, "size", len(raw))
