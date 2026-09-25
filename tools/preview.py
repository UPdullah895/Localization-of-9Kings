"""Render built Arabic strings the way TMP draws them, without starting the game.

TMP draws a string left to right, glyph by glyph, by cmap and advance width,
with no shaping, reordering or mark positioning; so does PIL's BASIC layout.
The stored text is already visual, so a correct preview here means the game
receives correct text (the remaining unknowns are box sizes and colours).

    preview.py TERM [TERM ...]      -> work/preview.png
"""
from __future__ import annotations

import io
import re
import sys
from pathlib import Path

import UnityPy
from PIL import Image, ImageDraw, ImageFont

import i2

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build/data.unity3d"
OUT = ROOT / "work/preview.png"
TAG = re.compile(r"<[^<>]*>")


def main(terms: list[str]) -> None:
    env = UnityPy.load(str(BUILD))
    objs = {(o.assets_file.name, o.path_id): o for o in env.objects}
    src = i2.load(objs[("resources.assets", 12310)].get_raw_data())
    font_data = bytes(objs[("resources.assets", 923)].read_typetree()["m_FontData"])
    font = ImageFont.truetype(io.BytesIO(font_data), 40, layout_engine=ImageFont.Layout.BASIC)
    small = ImageFont.truetype(io.BytesIO(font_data), 18, layout_engine=ImageFont.Layout.BASIC)
    col = src.lang_index("ar-001")
    blocks = [(t, TAG.sub("", src.term(t).languages[col])) for t in terms]
    height = sum(30 + 56 * (text.count("\n") + 1) for _, text in blocks) + 20
    img = Image.new("RGB", (1100, height), "#1d2340")
    d = ImageDraw.Draw(img)
    y = 10
    for term, text in blocks:
        d.text((20, y), term, font=small, fill="#8a93c4")
        y += 26
        for line in text.split("\n"):
            w = d.textlength(line, font=font)
            d.text((1080 - w, y), line, font=font, fill="white")     # right-aligned, like RTL UI
            y += 56
        y += 4
    OUT.parent.mkdir(exist_ok=True)
    img.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main(sys.argv[1:])
