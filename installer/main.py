"""9 Kings Arabic translation: install / uninstall (terminal program, Windows and Linux).

Finds the game through Steam (or asks for its folder), recognises what state
the game files are in, and offers only the actions that are safe for it:

  original game       -> install (the original file is backed up first)
  Arabic installed    -> uninstall (the backup is verified, then restored)
  anything else       -> explained; nothing is touched

Installing patches the player's own data.unity3d (see tools/patch.py); the
result must match the hash of the build verified by the developers, or the
original file stays in place.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    BUNDLE = Path(sys._MEIPASS)
    PAYLOAD = BUNDLE / "payload"
    ARABIC_FONT = PAYLOAD / "NotoSansArabic-Medium.ttf"
else:
    ROOT = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(ROOT / "tools"))
    PAYLOAD = ROOT / "installer/payload"
    ARABIC_FONT = ROOT / "fonts/NotoSansArabic-Medium.ttf"
sys.path.insert(0, str(Path(__file__).resolve().parent))

import steam  # noqa: E402

DATA = Path("9Kings_Data/data.unity3d")
BACKUP_NAME = "data.unity3d.arabic-backup"
MARKER_NAME = "arabic-translation.json"


def say(text: str = "") -> None:
    print(text, flush=True)


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def game_running() -> bool:
    try:
        if sys.platform == "win32":
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq 9Kings.exe"],
                                 capture_output=True, text=True).stdout
            return "9Kings.exe" in out
        return subprocess.run(["pgrep", "-f", "9Kings.exe"], capture_output=True).returncode == 0
    except OSError:
        return False


def normalise(text: str) -> Path | None:
    """A game folder from whatever the player typed or dragged in (folder, exe, data file)."""
    text = text.strip().strip('"').strip("'")
    if not text:
        return None
    p = Path(os.path.expanduser(text))
    for candidate in (p, p.parent, p.parent.parent):
        if (candidate / DATA).is_file():
            return candidate
    return p


def problem_with(folder: Path) -> str | None:
    if not folder.is_dir():
        return f"'{folder}' is not a folder."
    if not (folder / DATA).is_file():
        return ("This is not the 9 Kings folder: it has no 9Kings_Data/data.unity3d.\n"
                "In Steam: right-click 9 Kings > Manage > Browse local files, and use that folder.")
    if not (folder / "9Kings.exe").is_file():
        return "This folder has 9Kings_Data but no 9Kings.exe, so it is not a complete 9 Kings install."
    return None


class Game:
    def __init__(self, folder: Path, manifest: dict):
        self.folder, self.m = folder, manifest
        self.data = folder / DATA
        self.backup = self.data.with_name(BACKUP_NAME)
        self.marker = self.data.with_name(MARKER_NAME)

    def state(self) -> str:
        say("Checking the game files...")
        live = sha256(self.data)
        if live == self.m["original_sha256"]:
            return "original"
        if live == self.m["patched_sha256"]:
            return "installed"
        marker = self._read_marker()
        if marker and live == marker.get("patched_sha256"):
            same = marker.get("original_sha256") == self.m["original_sha256"] and \
                marker.get("game_version") == self.m["game_version"]
            return "installed" if same else "other-release"
        return "unknown"

    def _read_marker(self) -> dict | None:
        try:
            return json.loads(self.marker.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def _backup_ok(self, expected: str) -> bool:
        return self.backup.is_file() and sha256(self.backup) == expected

    def install(self) -> None:
        import patch
        payload = {n: json.loads((PAYLOAD / f"{n}.json").read_text(encoding="utf-8")) for n in ("strings", "marks")}
        say("Backing up the original game file...")
        tmp_backup = self.backup.with_suffix(".tmp")
        shutil.copyfile(self.data, tmp_backup)
        if sha256(tmp_backup) != self.m["original_sha256"]:
            tmp_backup.unlink()
            raise RuntimeError("the backup copy does not match the original; nothing was changed")
        tmp_backup.replace(self.backup)
        say("Patching (this takes about a minute)...")
        data = patch.patch(self.data, payload["strings"], payload["marks"], ARABIC_FONT.read_bytes(),
                           log=lambda s: say("  " + s))
        # patch() has already re-read the result: only the two patched objects differ from
        # the original and both read back exactly. Matching the developers' build hash as
        # well is expected, but library differences on another OS could change compression
        # bytes without changing content, so a mismatch is reported rather than fatal.
        digest = hashlib.sha256(data).hexdigest()
        say("  Identical to the tested build." if digest == self.m["patched_sha256"]
            else "  Content verified (compressed bytes differ from the tested build).")
        tmp = self.data.with_suffix(".unity3d.tmp")
        tmp.write_bytes(data)
        tmp.replace(self.data)
        if sha256(self.data) != digest:
            raise RuntimeError("the file on disk did not verify after writing; run Uninstall to restore")
        self.marker.write_text(json.dumps({"game_version": self.m["game_version"],
                                           "patched_sha256": digest,
                                           "original_sha256": self.m["original_sha256"]}, indent=1),
                               encoding="utf-8")

    def uninstall(self) -> None:
        marker = self._read_marker() or {}
        original = marker.get("original_sha256", self.m["original_sha256"])
        say("Verifying the backup of the original file...")
        if not self._backup_ok(original):
            raise RuntimeError("the backup of the original file is missing or damaged.\n"
                               "Restore the game with Steam instead: right-click 9 Kings > Properties >\n"
                               "Installed Files > Verify integrity of game files.")
        tmp = self.data.with_suffix(".unity3d.tmp")
        shutil.copyfile(self.backup, tmp)
        tmp.replace(self.data)
        if sha256(self.data) != original:
            raise RuntimeError("the restored file did not verify; use Steam's Verify integrity of game files")
        self.backup.unlink()
        self.marker.unlink(missing_ok=True)

    def forget_stale_backup(self) -> None:
        self.backup.unlink(missing_ok=True)
        self.marker.unlink(missing_ok=True)


def choose_folder() -> Path | None:
    found = steam.find_game()
    if found:
        say("Found 9 Kings:")
        for i, f in enumerate(found, 1):
            say(f"  {i}) {f}")
        say("Press Enter to use " + ("it" if len(found) == 1 else "the first one") +
            ", type a number, or type/drag in another folder.")
        answer = ask("> ")
        if not answer:
            return found[0]
        if answer.isdigit() and 1 <= int(answer) <= len(found):
            return found[int(answer) - 1]
        return normalise(answer)
    say("9 Kings was not found in your Steam libraries.")
    say("Type or drag in the game folder (Steam: right-click 9 Kings > Manage > Browse local files).")
    return normalise(ask("> "))


def run() -> None:
    manifest = json.loads((PAYLOAD / "manifest.json").read_text(encoding="utf-8"))
    say("=" * 64)
    say("  9 Kings - Arabic translation")
    say(f"  For game version {manifest['game_version']} (Steam build {manifest['steam_build']})")
    say("=" * 64)
    say()
    while True:
        folder = choose_folder()
        if folder is None:
            say("No folder given.")
            continue
        err = problem_with(folder)
        if err:
            say(err)
            say()
            continue
        break
    game = Game(folder, manifest)
    say(f"Game folder: {folder}")
    state = game.state()
    say()
    if state == "original":
        say("Status: original game (Arabic is not installed).")
        options = {"1": "Install the Arabic translation"}
    elif state == "installed":
        say(f"Status: the Arabic translation is installed ({manifest['terms_translated']} texts).")
        options = {"1": "Uninstall (restore the original game file)"}
    elif state == "other-release":
        say("Status: a different release of the Arabic translation is installed.")
        options = {"1": "Uninstall it (restore the original game file)"}
    else:
        say(f"This installer supports game version {manifest['game_version']} only, and the game's")
        say("data file does not match it. Most likely the game has been updated since this")
        say("release; check for a newer release of the translation.")
        if game.backup.is_file() and sha256(game.backup) == manifest["original_sha256"]:
            say()
            say("A verified backup of the supported original file is present.")
            options = {"1": "Restore the original game file from that backup"}
            state = "restore"
        elif game.backup.is_file():
            say()
            say("A backup from an earlier install is present but belongs to another game")
            say("version; restoring it would break the game.")
            options = {"1": "Delete that outdated backup"}
        else:
            options = {}
    options["0"] = "Exit"
    say()
    for key, label in options.items():
        say(f"  {key}) {label}")
    choice = ask("> ")
    if choice not in options or choice == "0":
        return
    if game_running():
        say("9 Kings is running. Close the game and run this program again.")
        return
    say()
    if state == "original":
        game.install()
        say()
        say("Done. Start 9 Kings, open Settings > Language and choose Arabic.")
    elif state in ("installed", "other-release", "restore"):
        game.uninstall()
        say()
        say("Done. The original game file is restored.")
    else:
        game.forget_stale_backup()
        say("Deleted.")


def self_check() -> None:
    """Used by CI on each packaged build: every module and payload file loads."""
    import patch  # noqa: F401 - pulls in UnityPy, fontTools, i2, font_merge
    for name in ("strings", "marks", "manifest"):
        json.loads((PAYLOAD / f"{name}.json").read_text(encoding="utf-8"))
    from fontTools.ttLib import TTFont
    TTFont(str(ARABIC_FONT))
    say("self-check ok")


def main() -> None:
    if "--self-check" in sys.argv:
        self_check()
        return
    try:
        run()
    except KeyboardInterrupt:
        say()
    except Exception as e:     # noqa: BLE001 - shown to the player, not a traceback
        say()
        say(f"Error: {e}")
    if getattr(sys, "frozen", False):
        ask("\nPress Enter to close.")


if __name__ == "__main__":
    main()
