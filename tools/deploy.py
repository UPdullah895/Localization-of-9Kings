"""Install or remove the Arabic build in the Steam copy of 9 Kings.

    deploy.py install [GAME_DIR]   copy build/data.unity3d into the game
    deploy.py restore [GAME_DIR]   put the pristine original/data.unity3d back
    deploy.py status  [GAME_DIR]   say which version the game currently has

GAME_DIR is optional: without it the Steam libraries are searched, which is
where the game may live on another drive.

Refuses to touch the game while it is running, and refuses to install over a
build of ours made for another game version (that file belongs to different
game data). The pristine copy in original/ is the backup; install also writes
the game-side backup and marker the released installer uses, so a later
Uninstall from the installer restores the right file. Every install records
the installed file's md5 in build/installed.md5, so the game's file is always
recognised as the original, the current build, or a previous build of ours;
anything else (e.g. a game update) is never overwritten.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "installer"))

import steam  # noqa: E402

ORIGINAL = ROOT / "original/data.unity3d"
BUILD = ROOT / "build/data.unity3d"
INSTALLED = ROOT / "build/installed.md5"
MANIFEST = ROOT / "installer/payload/manifest.json"
BACKUP_NAME = "data.unity3d.arabic-backup"
MARKER_NAME = "arabic-translation.json"


def game_data(folder: str | None = None) -> Path:
    if folder:
        return Path(folder).expanduser() / "9Kings_Data/data.unity3d"
    found = steam.find_game()
    if not found:
        raise SystemExit("9 Kings was not found in the Steam libraries; pass the game folder.")
    return found[0] / "9Kings_Data/data.unity3d"


def md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def game_running() -> bool:
    # Match the process name exactly, and the full path only when it ends at the
    # executable: a bare "9Kings.exe" pattern also matches any shell whose command
    # line merely mentions it (a terminal that just ran this tool, for example).
    mine = os.getpid()
    for args in (["-x", "9Kings.exe"], ["-f", r"(^|/)9Kings\.exe( |$)"]):
        res = subprocess.run(["pgrep", *args], capture_output=True, text=True)
        for pid in res.stdout.split():
            if pid.isdigit() and int(pid) != mine:
                return True
    return False


def state(live_path: Path) -> str:
    live = md5(live_path)
    if live == md5(ORIGINAL):
        return "original"
    if BUILD.exists() and live == md5(BUILD):
        return "arabic-build"
    if INSTALLED.exists() and live == INSTALLED.read_text().strip():
        return "previous-arabic-build"
    return "unknown"


def copy(src: Path, live_path: Path) -> None:
    tmp = live_path.with_suffix(".unity3d.tmp")
    shutil.copyfile(src, tmp)
    tmp.replace(live_path)
    if md5(live_path) != md5(src):
        raise SystemExit("copy verification failed")


def keep_backup(src: Path, live_path: Path) -> None:
    """Write the game-side backup and marker the released installer depends on.

    `src` is the pristine original for the supported version: the game's own copy
    when it is untouched, else original/. A backup left over from an earlier game
    version is replaced, because restoring it later would put old game data back.
    """
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    tmp = live_path.with_name(BACKUP_NAME).with_suffix(".tmp")
    shutil.copyfile(src, tmp)
    digest = hashlib.sha256(tmp.read_bytes()).hexdigest()
    if digest != manifest["original_sha256"]:
        tmp.unlink(missing_ok=True)
        raise SystemExit("the original file does not match the installer manifest; nothing was changed")
    tmp.replace(live_path.with_name(BACKUP_NAME))
    live_path.with_name(MARKER_NAME).write_text(json.dumps(
        {"game_version": manifest["game_version"],
         "original_sha256": manifest["original_sha256"],
         "steam_build": manifest["steam_build"]}, indent=1), encoding="utf-8")


def main(cmd: str, folder: str | None = None) -> None:
    live_path = game_data(folder)
    current = state(live_path)
    if cmd == "status":
        print(current)
        return
    if game_running():
        raise SystemExit("9 Kings is running — close it first.")
    if current == "unknown":
        raise SystemExit("The game's data.unity3d matches neither the original nor our build "
                         "(game update?). Verify game files in Steam, then re-copy original/.")
    if cmd == "install":
        if current == "previous-arabic-build":
            raise SystemExit("The game currently carries an older Arabic build; its version is not "
                             "known, so installing this one could mix two game versions.\n"
                             "Verify the game files in Steam (Properties > Installed Files) and run "
                             "install again.")
        if current == "arabic-build":
            print("already the current build; refreshing its backup from original/")
            keep_backup(ORIGINAL, live_path)
        else:
            keep_backup(live_path, live_path)
        copy(BUILD, live_path)
        INSTALLED.write_text(md5(BUILD))
    elif cmd == "restore":
        copy(ORIGINAL, live_path)
    else:
        raise SystemExit(__doc__)
    print(f"{current} -> {state(live_path)}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "status",
         sys.argv[2] if len(sys.argv) > 2 else None)
