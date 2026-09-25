"""Find 9 Kings in the player's Steam libraries (Windows and Linux)."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

APP_ID = "2784470"
GAME_DIR = "9 Kings"


def _steam_roots() -> list[Path]:
    roots: list[Path] = []
    if sys.platform == "win32":
        try:
            import winreg
            for hive, key, value in ((winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                                     (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                                     (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath")):
                try:
                    with winreg.OpenKey(hive, key) as k:
                        roots.append(Path(winreg.QueryValueEx(k, value)[0]))
                except OSError:
                    pass
        except ImportError:
            pass
        for env in ("ProgramFiles(x86)", "ProgramFiles"):
            if os.environ.get(env):
                roots.append(Path(os.environ[env]) / "Steam")
    else:
        home = Path.home()
        roots += [home / ".local/share/Steam", home / ".steam/steam", home / ".steam/root",
                  home / ".var/app/com.valvesoftware.Steam/.local/share/Steam",   # Flatpak
                  home / "snap/steam/common/.local/share/Steam"]                   # Snap
    return roots


def _libraries(root: Path) -> list[Path]:
    libs = [root]
    vdf = root / "steamapps/libraryfolders.vdf"
    try:
        text = vdf.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return libs
    for m in re.finditer(r'"path"\s+"([^"]+)"', text):
        libs.append(Path(m.group(1).replace("\\\\", "\\")))
    return libs


def find_game() -> list[Path]:
    """Every 9 Kings install folder found, most likely first, without duplicates."""
    found: list[Path] = []
    seen: set[str] = set()
    for root in _steam_roots():
        for lib in _libraries(root):
            game = lib / "steamapps/common" / GAME_DIR
            try:
                key = str(game.resolve()).lower()
            except OSError:
                continue
            if key not in seen and (game / "9Kings_Data/data.unity3d").is_file():
                seen.add(key)
                found.append(game)
    return found
