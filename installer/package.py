"""Package the installer as one self-contained program (run on the target OS).

    python installer/package.py      -> dist/9Kings-Arabic(.exe)

The GitHub workflow runs this on Windows and Linux. The payload (translated
strings, harakat glyph spec, manifest) comes from tools/build.py and is
committed, so packaging needs no game files.
"""
import os
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent.parent

PyInstaller.__main__.run([
    str(ROOT / "installer/main.py"),
    "--onefile", "--console", "--noconfirm", "--clean",
    "--name", "9Kings-Arabic",
    "--paths", str(ROOT / "tools"),
    "--paths", str(ROOT / "installer"),
    "--hidden-import", "patch",
    "--collect-all", "UnityPy",
    "--add-data", f"{ROOT / 'installer/payload'}{os.pathsep}payload",
    "--add-data", f"{ROOT / 'fonts/NotoSansArabic-Medium.ttf'}{os.pathsep}payload",
    "--add-data", f"{ROOT / 'fonts/OFL.txt'}{os.pathsep}payload",
    "--distpath", str(ROOT / "dist"),
    "--workpath", str(ROOT / "build/pyinstaller"),
    "--specpath", str(ROOT / "build/pyinstaller"),
])
print("built", *sorted((ROOT / "dist").iterdir()), file=sys.stderr)
