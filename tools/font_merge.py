"""Merge Noto Sans Arabic glyphs into the game's NotoSans-Medium TTF.

The game's NotoSans TMP font assets (normal and outlined) are dynamic: TMP
rasterizes glyphs at runtime from the embedded NotoSans-Medium `Font`. Adding
Arabic glyphs to that TTF makes them available to every text that falls back
to NotoSans, which is the chain Arabic already uses.

I2 Localization shapes Arabic into presentation-form codepoints (U+FB50-FDFF,
U+FE70-FEFC) before TMP sees it, and TMP only looks glyphs up through `cmap`,
so the merged font must map those codepoints; Noto Sans Arabic does.

Left overhangs: some isolated/final forms (reh, zain and relatives) have a
tail that reaches left of the glyph origin, into the next letter's space.
Shaping engines keep them apart with GPOS kerning, which TMP does not apply,
and the outlined header font thickens both glyphs until they merge. Isolated
and final forms never join on their left, so for those codepoints the cmap is
pointed at a copy of the glyph shifted right to a positive left bearing, with
the advance widened by the same amount; the right (joining) edge is unchanged.
The original glyphs stay in place for GSUB and composites.

`merge()` verifies its own output: every codepoint the game font mapped still
draws the same outline with the same advance, and every added Arabic codepoint
draws exactly what Noto Sans Arabic draws (moved right by the shift, if any).
"""
from __future__ import annotations

import io
import unicodedata

from fontTools.merge import Merger
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont

ARABIC_RANGES = [(0x0600, 0x0700), (0x0750, 0x0780), (0x08A0, 0x0900), (0xFB50, 0xFE00), (0xFE70, 0xFF00)]

# Tables whose values must stay the game font's: vertical metrics, naming, identity.
KEEP_FROM_BASE = ("head", "hhea", "OS/2", "name", "post", "STAT", "gasp", "prep")

# Left side bearing, in font units (1000/em), given to non-left-joining forms whose
# baseline-level outline crosses the origin. Forms with a non-negative bearing are left alone.
LEFT_CLEARANCE = 60
# Only contours that reach below this height count as tails; marks above the letter
# (madda, shadda) overhang harmlessly over the neighbour and are ignored.
TAIL_TOP = 100


def _is_arabic(cp: int) -> bool:
    return any(lo <= cp < hi for lo, hi in ARABIC_RANGES)


def _is_non_left_joining_letter(cp: int) -> bool:
    """An Arabic letter form that never connects to the letter on its left (visual order):
    isolated and final presentation forms, and base letters (drawn isolated when unshaped)."""
    tag = unicodedata.decomposition(chr(cp)).split(" ")[0]
    if tag in ("<isolated>", "<final>"):
        return True
    return not tag and unicodedata.category(chr(cp)) == "Lo"


def _drawing(font: TTFont, cp: int, dx: int = 0):
    """Decomposed outline and advance. With dx, the outline is moved right by dx and
    normalised through TTGlyphPen, which drops redundant closing segments; use
    _normalised_drawing on the other side of such a comparison."""
    name = font.getBestCmap()[cp]
    gs = font.getGlyphSet()
    pen = DecomposingRecordingPen(gs)
    if dx:
        tt = TTGlyphPen(gs)
        gs[name].draw(TransformPen(tt, (1, 0, 0, 1, dx, 0)))
        tt.glyph().draw(pen, font["glyf"])
    else:
        gs[name].draw(pen)
    return pen.value, font["hmtx"][name][0] + dx


def _normalised_drawing(font: TTFont, cp: int):
    name = font.getBestCmap()[cp]
    gs = font.getGlyphSet()
    tt = TTGlyphPen(gs)
    gs[name].draw(tt)
    pen = DecomposingRecordingPen(gs)
    tt.glyph().draw(pen, font["glyf"])
    return pen.value, font["hmtx"][name][0]


def _x_min(font: TTFont, glyph: str) -> float | None:
    gs = font.getGlyphSet()
    pen = BoundsPen(gs)
    gs[glyph].draw(pen)
    return pen.bounds[0] if pen.bounds else None


def _tail_x_min(font: TTFont, glyph: str) -> float | None:
    """Leftmost x of the glyph's contours that reach down to the baseline or below."""
    gs = font.getGlyphSet()
    rec = DecomposingRecordingPen(gs)
    gs[glyph].draw(rec)
    x_min, contour = None, []
    for op, args in rec.value:
        contour.append((op, args))
        if op in ("closePath", "endPath"):
            pen = BoundsPen(gs)
            for cop, cargs in contour:
                getattr(pen, cop)(*cargs)
            contour = []
            if pen.bounds and pen.bounds[1] < TAIL_TOP:
                x_min = pen.bounds[0] if x_min is None else min(x_min, pen.bounds[0])
    return x_min


def _clear_left_overhangs(font: TTFont, codepoints: list[int]) -> dict[int, int]:
    """Point overhanging non-left-joining codepoints at shifted glyph copies; returns cp -> shift."""
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    order = list(font.getGlyphOrder())
    copies: dict[str, tuple[str, int]] = {}
    shifts: dict[int, int] = {}
    for cp in codepoints:
        if not _is_non_left_joining_letter(cp):
            continue
        glyph = cmap[cp]
        if glyph not in copies:
            x_min = _tail_x_min(font, glyph)
            if x_min is None or x_min >= 0:
                continue
            dx = int(round(LEFT_CLEARANCE - x_min))
            pen = TTGlyphPen(gs)
            gs[glyph].draw(TransformPen(pen, (1, 0, 0, 1, dx, 0)))
            new = f"{glyph}.lclear"
            font["glyf"][new] = pen.glyph()
            font["glyf"][new].recalcBounds(font["glyf"])
            font["hmtx"][new] = (font["hmtx"][glyph][0] + dx, font["glyf"][new].xMin)
            order.append(new)
            copies[glyph] = (new, dx)
        new, dx = copies[glyph]
        for table in font["cmap"].tables:
            if table.isUnicode() and cp in table.cmap:
                table.cmap[cp] = new
        shifts[cp] = dx
    font.setGlyphOrder(order)
    return shifts


def _load(data: bytes) -> TTFont:
    return TTFont(io.BytesIO(data))


def merge(base_ttf: bytes, arabic_ttf: bytes) -> tuple[bytes, int, int, int]:
    base, arabic = _load(base_ttf), _load(arabic_ttf)
    if base["head"].unitsPerEm != arabic["head"].unitsPerEm:
        raise ValueError("unitsPerEm differs; glyphs would need scaling")
    base_cmap = base.getBestCmap()
    added = sorted(cp for cp in arabic.getBestCmap() if _is_arabic(cp) and cp not in base_cmap)
    if not added:
        raise ValueError("no Arabic codepoints to add")

    # The merger keeps the first font's glyph for codepoints both fonts map.
    merged = Merger().merge([io.BytesIO(base_ttf), io.BytesIO(arabic_ttf)])
    for tag in KEEP_FROM_BASE:
        if tag in base:
            merged[tag] = base[tag]
    shifts = _clear_left_overhangs(merged, added)
    out = io.BytesIO()
    merged.save(out)
    data = out.getvalue()

    check = _load(data)
    cmap = check.getBestCmap()
    for cp in base_cmap:
        if _drawing(check, cp) != _drawing(base, cp):
            raise ValueError(f"U+{cp:04X} changed from the game font")
    for cp in added:
        actual = _normalised_drawing(check, cp) if cp in shifts else _drawing(check, cp)
        if cp not in cmap or actual != _drawing(arabic, cp, shifts.get(cp, 0)):
            raise ValueError(f"U+{cp:04X} not copied faithfully from Noto Sans Arabic")
        if cp in shifts and _tail_x_min(check, cmap[cp]) < LEFT_CLEARANCE - 1:
            raise ValueError(f"U+{cp:04X} still overhangs")
    if check["maxp"].numGlyphs != len(check.getGlyphOrder()):
        raise ValueError("maxp glyph count inconsistent")
    if check["head"].unitsPerEm != base["head"].unitsPerEm or check["hhea"].ascent != base["hhea"].ascent:
        raise ValueError("vertical metrics changed")
    return data, len(base_cmap), len(added), len(shifts)
