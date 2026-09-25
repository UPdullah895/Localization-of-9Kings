"""Inventory data.unity3d: object types, and whether MonoBehaviour type trees are present."""
import collections, sys
import UnityPy

env = UnityPy.load("original/data.unity3d")
types = collections.Counter()
for obj in env.objects:
    types[obj.type.name] += 1
for name, n in types.most_common(25):
    print(f"{n:6d}  {name}")
for f in env.files.values():
    sf_list = getattr(f, "files", {}) or {}
    for name, sf in sf_list.items():
        if hasattr(sf, "enable_type_tree"):
            print("file", name, "type_tree:", sf.enable_type_tree)
