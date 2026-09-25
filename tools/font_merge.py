"""Merge Noto Sans Arabic glyphs into the game's NotoSans-Medium TTF.

The game's NotoSans TMP font assets (normal and outlined) are dynamic: TMP
rasterizes glyphs at runtime from the embedded NotoSans-Medium `Font`. Adding
Arabic glyphs to that TTF makes them available to every text that falls back
to NotoSans, which is the chain Arabic already uses.

I2 Localization shapes Arabic into presentation-form codepoints (U+FB50-FDFF,
U+FE70-FEFC) before TMP sees it, and TMP only looks glyphs up through `cmap`,
so the merged font must map those codepoints; Noto Sans Arabic does.

`merge()` verifies its own output: every codepoint the game font mapped still
draws the same outline with the same advance, and every added Arabic codepoint
draws exactly what Noto Sans Arabic draws.
"""
from __future__ import annotations

import io

from fontTools.merge import Merger
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.ttLib import TTFont

ARABIC_RANGES = [(0x0600, 0x0700), (0x0750, 0x0780), (0x08A0, 0x0900), (0xFB50, 0xFE00), (0xFE70, 0xFF00)]

# Tables whose values must stay the game font's: vertical metrics, naming, identity.
KEEP_FROM_BASE = ("head", "hhea", "OS/2", "name", "post", "STAT", "gasp", "prep")


def _is_arabic(cp: int) -> bool:
    return any(lo <= cp < hi for lo, hi in ARABIC_RANGES)


def _drawing(font: TTFont, cp: int):
    name = font.getBestCmap()[cp]
    gs = font.getGlyphSet()
    pen = DecomposingRecordingPen(gs)
    gs[name].draw(pen)
    return pen.value, font["hmtx"][name][0]


def _load(data: bytes) -> TTFont:
    return TTFont(io.BytesIO(data))


def merge(base_ttf: bytes, arabic_ttf: bytes) -> bytes:
    base, arabic = _load(base_ttf), _load(arabic_ttf)
    if base["head"].unitsPerEm != arabic["head"].unitsPerEm:
        raise ValueError("unitsPerEm differs; glyphs would need scaling")
    base_cmap = base.getBestCmap()
    added = sorted(cp for cp in arabic.getBestCmap() if _is_arabic(cp) and cp not in base_cmap)
    if not added:
        raise ValueError("no Arabic codepoints to add")

    # The merger needs files; it keeps the first font's glyph for shared codepoints.
    merged = Merger().merge([io.BytesIO(base_ttf), io.BytesIO(arabic_ttf)])
    for tag in KEEP_FROM_BASE:
        if tag in base:
            merged[tag] = base[tag]
    out = io.BytesIO()
    merged.save(out)
    data = out.getvalue()

    check = _load(data)
    cmap = check.getBestCmap()
    for cp in base_cmap:
        if _drawing(check, cp) != _drawing(base, cp):
            raise ValueError(f"U+{cp:04X} changed from the game font")
    for cp in added:
        if cp not in cmap or _drawing(check, cp) != _drawing(arabic, cp):
            raise ValueError(f"U+{cp:04X} not copied faithfully from Noto Sans Arabic")
    if check["head"].unitsPerEm != base["head"].unitsPerEm or check["hhea"].ascent != base["hhea"].ascent:
        raise ValueError("vertical metrics changed")
    return data, len(base_cmap), len(added)
