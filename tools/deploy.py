"""Install or remove the Arabic build in the Steam copy of 9 Kings.

    deploy.py install   copy build/data.unity3d into the game
    deploy.py restore   put the pristine original/data.unity3d back
    deploy.py status    say which version the game currently has

Refuses to touch the game while it is running. The pristine copy in original/
is the backup. Every install records the installed file's md5 in
build/installed.md5, so the game's file is always recognised as the original,
the current build, or a previous build of ours; anything else (e.g. a game
update) is never overwritten.
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GAME_DATA = Path.home() / ".local/share/Steam/steamapps/common/9 Kings/9Kings_Data/data.unity3d"
ORIGINAL = ROOT / "original/data.unity3d"
BUILD = ROOT / "build/data.unity3d"
INSTALLED = ROOT / "build/installed.md5"


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def game_running() -> bool:
    return subprocess.run(["pgrep", "-if", "9Kings.exe"], capture_output=True).returncode == 0


def state() -> str:
    live = md5(GAME_DATA)
    if live == md5(ORIGINAL):
        return "original"
    if BUILD.exists() and live == md5(BUILD):
        return "arabic-build"
    if INSTALLED.exists() and live == INSTALLED.read_text().strip():
        return "previous-arabic-build"
    return "unknown"


def copy(src: Path) -> None:
    tmp = GAME_DATA.with_suffix(".unity3d.tmp")
    shutil.copyfile(src, tmp)
    tmp.replace(GAME_DATA)
    if md5(GAME_DATA) != md5(src):
        raise SystemExit("copy verification failed")


def main(cmd: str) -> None:
    current = state()
    if cmd == "status":
        print(current)
        return
    if game_running():
        raise SystemExit("9 Kings is running — close it first.")
    if current == "unknown":
        raise SystemExit("The game's data.unity3d matches neither the original nor our build "
                         "(game update?). Verify game files in Steam, then re-copy original/.")
    if cmd == "install":
        copy(BUILD)
        INSTALLED.write_text(md5(BUILD))
    elif cmd == "restore":
        copy(ORIGINAL)
    else:
        raise SystemExit(__doc__)
    print(f"{current} -> {state()}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "status")
