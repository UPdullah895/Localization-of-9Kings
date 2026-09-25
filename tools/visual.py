"""Turn logical Arabic into the visual form TextMesh Pro draws correctly.

TMP has no Arabic shaping, no bidirectional layout, and no mark positioning.
I2 Localization's built-in RTL fix tries to fill the gap at runtime, but in
this game it breaks: it wraps a reversed string (so wrapped lines come out
bottom-to-top), splits `<color=#{KINGCOLOR}>` at the inner brace, swaps
{VAR1}/{VAR2}, and misplaces harakat. So the Arabic column is registered
under a language code I2 does not treat as RTL, and every string is stored
already in its final visual form, made here:

1. Tags and placeholders are lifted out; every character remembers which
   tags enclose it.
2. Lines are wrapped (when the term has a width limit) at word boundaries,
   measured with the real glyph advances of the game's merged font, because a
   visual-order line that TMP wraps by itself comes out with its lines in
   reverse order.
3. Each line is shaped into presentation forms (with lam-alef ligatures).
4. Harakat on a letter become one zero-width glyph placed with the font's own
   GPOS anchors for that exact letter form (`MarkGlyphs`), since TMP would
   otherwise stack every mark at the same spot regardless of the letter.
5. Each line is reordered with the Unicode bidirectional algorithm (paragraph
   direction RTL, no explicit embeddings), and mirrored characters are swapped.
6. Tags are re-emitted around the characters they enclosed, in visual order.

Placeholders are substituted by the game after translation, so each is kept
as a unit; {VAR1}-style values are numbers and act as European digits in the
bidi algorithm, {KING}/{DIFFICULTY} are words and act as Arabic letters.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from arabic_reshaper.letters import FINAL, INITIAL, ISOLATED, LETTERS_ARABIC, MEDIAL
from fontTools.ttLib import TTFont

TAG = re.compile(r"<[^<>]*>")
PLACEHOLDER = re.compile(r"\{[A-Za-z0-9_]+\}")
TOKEN = re.compile(f"{TAG.pattern}|{PLACEHOLDER.pattern}")
WORD_PLACEHOLDERS = {"{KING}", "{DIFFICULTY}"}
# Width assumed for a substituted value when wrapping, in em: "+50%" or a king's name.
NUMBER_WIDTH, WORD_WIDTH = 2.5, 6.0

LAM = "ل"
LAM_ALEF = {"آ": ("ﻵ", "ﻶ"), "أ": ("ﻷ", "ﻸ"),
            "إ": ("ﻹ", "ﻺ"), "ا": ("ﻻ", "ﻼ")}
MIRROR = dict(zip("()[]{}<>«»‹›", ")(][}{><»«›‹"))
PUA_START = 0xE000


@dataclass
class Unit:
    text: str          # one character, or a whole placeholder like "{VAR1}"
    tags: tuple        # full opening tags enclosing it, outermost first
    cls: str = ""      # bidi class override (placeholders)
    marks: str = ""    # harakat attached to this letter


def _parse(line: str, stack: list[str]) -> list[Unit]:
    """Split one line into units. `stack` carries open tags across lines and is updated."""
    units, pos = [], 0
    for m in TOKEN.finditer(line):
        units += [Unit(c, tuple(stack)) for c in line[pos:m.start()]]
        tok = m.group()
        if tok.startswith("</"):
            name = tok[2:-1]
            if not stack or _tag_name(stack[-1]) != name:
                raise ValueError(f"unbalanced {tok} in {line!r}")
            stack.pop()
        elif tok.startswith("<"):
            stack.append(tok)
        else:
            units.append(Unit(tok, tuple(stack), "R" if tok in WORD_PLACEHOLDERS else "EN"))
        pos = m.end()
    units += [Unit(c, tuple(stack)) for c in line[pos:]]
    return units


def _tag_name(tag: str) -> str:
    return re.match(r"<([a-zA-Z]+)", tag).group(1)


def _is_mark(u: Unit) -> bool:
    return not u.cls and unicodedata.category(u.text) == "Mn"


# --- shaping ---------------------------------------------------------------

def _forms(c: str):
    return LETTERS_ARABIC.get(c)


def _joins_next(c: str) -> bool:
    f = _forms(c)
    return bool(f and f[INITIAL])


def _joins_prev(c: str) -> bool:
    f = _forms(c)
    return bool(f and f[FINAL])


def _attach_marks(units: list[Unit]) -> list[Unit]:
    out = []
    for u in units:
        if _is_mark(u):
            if not out or out[-1].cls or not _forms(out[-1].text):
                raise ValueError(f"mark U+{ord(u.text):04X} not on an Arabic letter")
            out[-1].marks += u.text
        else:
            out.append(u)
    return out


def _shape(units: list[Unit]) -> list[Unit]:
    """Presentation forms; lam+alef become one ligature unit (the alef's marks move onto it)."""
    units = _attach_marks(units)
    out = []
    i = 0
    while i < len(units):
        u = units[i]
        c = u.text
        if u.cls or not _forms(c):
            out.append(u)
            i += 1
            continue
        prev_joins = i > 0 and not units[i - 1].cls and _joins_next(units[i - 1].text) and _joins_prev(c)
        nxt = units[i + 1] if i + 1 < len(units) else None
        if c == LAM and nxt and not nxt.cls and nxt.text in LAM_ALEF:
            lig = LAM_ALEF[nxt.text][1 if prev_joins else 0]
            out.append(Unit(lig, u.tags, marks=u.marks + nxt.marks))
            i += 2
            continue
        next_joins = bool(nxt) and not nxt.cls and _joins_prev(nxt.text) and _joins_next(c)
        f = _forms(c)
        if prev_joins and next_joins and f[MEDIAL]:
            form = f[MEDIAL]
        elif prev_joins:
            form = f[FINAL]
        elif next_joins:
            form = f[INITIAL]
        else:
            form = f[ISOLATED]
        out.append(Unit(form, u.tags, marks=u.marks))
        i += 1
    return out


# --- marks -----------------------------------------------------------------

class MarkGlyphs:
    """Zero-width glyphs, one per (letter form, harakat) pair, positioned by GPOS anchors.

    Each gets a Private Use codepoint; `spec()` describes them for font_merge.add_marks.
    In visual order the mark glyph sits immediately left of its letter with zero
    advance, so it is drawn from the letter's origin, exactly where the anchors place it.
    """

    def __init__(self, noto: TTFont, merged: TTFont):
        self.noto, self.merged = noto, merged
        self.noto_cmap, self.merged_cmap = noto.getBestCmap(), merged.getBestCmap()
        self.base_anchor, self.mkmk_anchor = self._anchors(noto)
        self.bases = {g for g, _ in self.base_anchor}
        self.glyphs: dict[tuple[str, str], tuple[str, list]] = {}   # (form char, marks) -> (pua char, parts)

    @staticmethod
    def _anchors(font: TTFont):
        base, mkmk = {}, {}
        for lookup in font["GPOS"].table.LookupList.Lookup:
            for st in lookup.SubTable:
                kind = lookup.LookupType
                if kind == 9:
                    st, kind = st.ExtSubTable, st.ExtensionLookupType
                if kind == 4:
                    classes = {g: (r.Class, r.MarkAnchor) for g, r in zip(st.MarkCoverage.glyphs, st.MarkArray.MarkRecord)}
                    for g, rec in zip(st.BaseCoverage.glyphs, st.BaseArray.BaseRecord):
                        for m, (cls, anchor) in classes.items():
                            a = rec.BaseAnchor[cls]
                            if a is not None and (g, m) not in base:
                                base[(g, m)] = (a.XCoordinate - anchor.XCoordinate, a.YCoordinate - anchor.YCoordinate)
                elif kind == 6:
                    classes = {g: (r.Class, r.MarkAnchor) for g, r in zip(st.Mark1Coverage.glyphs, st.Mark1Array.MarkRecord)}
                    for g, rec in zip(st.Mark2Coverage.glyphs, st.Mark2Array.Mark2Record):
                        for m, (cls, anchor) in classes.items():
                            a = rec.Mark2Anchor[cls]
                            if a is not None and (g, m) not in mkmk:
                                mkmk[(g, m)] = (a.XCoordinate - anchor.XCoordinate, a.YCoordinate - anchor.YCoordinate)
        return base, mkmk

    def get(self, form: str, marks: str) -> str:
        key = (form, marks)
        if key not in self.glyphs:
            self.glyphs[key] = (chr(PUA_START + len(self.glyphs)), self._place(form, marks))
        return self.glyphs[key][0]

    def _place(self, form: str, marks: str) -> list[tuple[str, int, int]]:
        name = self.noto_cmap[ord(form)]
        # Forms shifted right by font_merge (left clearance) carry their anchors with them.
        dx = self.merged["hmtx"][self.merged_cmap[ord(form)]][0] - self.noto["hmtx"][name][0]
        base, bx, by, dots = name, 0, 0, []
        glyph = self.noto["glyf"][name]
        if name not in self.bases and glyph.isComposite():
            # Dotted presentation forms are a dotless skeleton plus dot marks; the anchors
            # live on the skeleton, and harakat stack on the dots mark-to-mark.
            first, *rest = glyph.components
            base, bx, by = first.glyphName, first.x, first.y
            dots = [(c.glyphName, c.x, c.y) for c in rest]
        placed: list[tuple[str, int, int]] = []
        # Canonical order puts shadda after fatha/damma/kasra; place shadda first so the
        # vowel attaches to it (mark-to-mark), as a shaping engine would.
        for m in sorted(marks, key=lambda m: m != "\u0651"):
            mg = self.noto_cmap[ord(m)]
            pos = None
            for g, x, y in reversed(dots + placed):
                if (g, mg) in self.mkmk_anchor:
                    ax, ay = self.mkmk_anchor[(g, mg)]
                    pos = (x + ax, y + ay)
                    break
            if pos is None:
                if (base, mg) not in self.base_anchor:
                    raise ValueError(f"no anchor for U+{ord(m):04X} on {base} ({form!r})")
                ax, ay = self.base_anchor[(base, mg)]
                pos = (bx + ax, by + ay)
            placed.append((mg, *pos))
        return [(g, x + dx, y) for g, x, y in placed]

    def spec(self) -> dict[str, list[list]]:
        """{PUA codepoint hex: [[Noto Sans Arabic glyph name, x, y], ...]} for font_merge.add_marks."""
        return {f"{ord(pua):04X}": [list(p) for p in parts] for pua, parts in self.glyphs.values()}


def _apply_marks(units: list[Unit], marks: MarkGlyphs | None) -> list[Unit]:
    out = []
    for u in units:
        if u.marks:
            if marks is None:
                raise ValueError("harakat need a MarkGlyphs")
            # Logical order: mark glyph after its letter; the RTL reversal puts it on the left.
            out += [Unit(u.text, u.tags), Unit(marks.get(u.text, u.marks), u.tags, cls="NSM")]
        else:
            out.append(u)
    return out


# --- bidi ------------------------------------------------------------------

def _classes(units: list[Unit]) -> list[str]:
    return [u.cls or unicodedata.bidirectional(u.text) or "L" for u in units]


def _levels(units: list[Unit]) -> list[int]:
    """UBA for one line with paragraph level 1 and no explicit formatting characters."""
    t = _classes(units)
    n = len(t)
    prev = "R"                                   # W1: NSM takes the previous type (sos = R)
    for i in range(n):
        if t[i] == "NSM":
            t[i] = prev
        prev = t[i]
    strong = "R"                                 # W2, W3
    for i in range(n):
        if t[i] in ("L", "R", "AL"):
            strong = t[i]
        elif t[i] == "EN" and strong == "AL":
            t[i] = "AN"
    t = ["R" if x == "AL" else x for x in t]
    for i in range(1, n - 1):                    # W4
        if t[i] == "ES" and t[i - 1] == t[i + 1] == "EN":
            t[i] = "EN"
        elif t[i] == "CS" and t[i - 1] == t[i + 1] and t[i - 1] in ("EN", "AN"):
            t[i] = t[i - 1]
    i = 0                                        # W5
    while i < n:
        if t[i] == "ET":
            j = i
            while j < n and t[j] == "ET":
                j += 1
            if (i > 0 and t[i - 1] == "EN") or (j < n and t[j] == "EN"):
                t[i:j] = ["EN"] * (j - i)
            i = j
        else:
            i += 1
    t = ["ON" if x in ("ES", "ET", "CS") else x for x in t]   # W6
    strong = "R"                                 # W7
    for i in range(n):
        if t[i] in ("L", "R"):
            strong = t[i]
        elif t[i] == "EN" and strong == "L":
            t[i] = "L"
    neutral = ("B", "S", "WS", "ON", "BN", "LRI", "RLI", "FSI", "PDI")
    i = 0                                        # N1, N2
    while i < n:
        if t[i] in neutral:
            j = i
            while j < n and t[j] in neutral:
                j += 1
            before = "R" if i == 0 else ("R" if t[i - 1] in ("R", "EN", "AN") else "L")
            after = "R" if j == n else ("R" if t[j] in ("R", "EN", "AN") else "L")
            t[i:j] = [before if before == after else "R"] * (j - i)
            i = j
        else:
            i += 1
    levels = [1 if x == "R" else 2 for x in t]   # I2 (paragraph level 1)
    j = n                                        # L1: trailing whitespace to paragraph level
    while j > 0 and unicodedata.bidirectional(units[j - 1].text[0]) in ("WS", "S") and not units[j - 1].cls:
        j -= 1
        levels[j] = 1
    return levels


def _reorder(units: list[Unit]) -> list[Unit]:
    levels = _levels(units)
    order = list(range(len(units)))
    for level in (2, 1):                         # L2
        i = 0
        while i < len(order):
            if levels[order[i]] >= level:
                j = i
                while j < len(order) and levels[order[j]] >= level:
                    j += 1
                order[i:j] = order[i:j][::-1]
                i = j
            else:
                i += 1
    out = []
    for k in order:                              # L4
        u = units[k]
        if levels[k] % 2 and u.text in MIRROR and not u.cls:
            u = Unit(MIRROR[u.text], u.tags, u.cls)
        out.append(u)
    return out


def _emit(units: list[Unit]) -> str:
    s, open_ = [], []
    for u in units:
        common = 0
        while common < min(len(open_), len(u.tags)) and open_[common] == u.tags[common]:
            common += 1
        for tag in reversed(open_[common:]):
            s.append(f"</{_tag_name(tag)}>")
        s += list(u.tags[common:])
        open_ = list(u.tags)
        s.append(u.text)
    s += [f"</{_tag_name(tag)}>" for tag in reversed(open_)]
    return "".join(s)


# --- wrapping --------------------------------------------------------------

class Metrics:
    """Advance widths, in em, from the merged font."""

    def __init__(self, font: TTFont):
        self.cmap, self.hmtx = font.getBestCmap(), font["hmtx"]
        self.upem = font["head"].unitsPerEm

    def width(self, units: list[Unit]) -> float:
        w = 0.0
        for u in units:
            if u.cls == "EN":
                w += NUMBER_WIDTH
            elif u.cls == "R":
                w += WORD_WIDTH
            elif ord(u.text) in self.cmap:
                w += self.hmtx[self.cmap[ord(u.text)]][0] / self.upem
        return w


def _wrap(units: list[Unit], max_em: float, metrics: Metrics) -> list[list[Unit]]:
    words, cur = [], []
    for u in units:
        if u.text == " " and not u.cls:
            words.append(cur)
            cur = []
        else:
            cur.append(u)
    words.append(cur)
    space = metrics.width([Unit(" ", ())])
    lines, line, width = [], [], 0.0
    for word in words:
        w = metrics.width(word)
        if line and width + space + w > max_em:
            lines.append(line)
            line, width = [], 0.0
        if line:
            line.append(Unit(" ", word[0].tags if word else line[-1].tags))
            width += space
        line += word
        width += w
    lines.append(line)
    return lines


# --- entry point -----------------------------------------------------------

def visual(text: str, marks: MarkGlyphs | None = None, metrics: Metrics | None = None,
           max_em: float | None = None) -> str:
    """Logical Arabic (with tags, placeholders, \\n) -> visual-order text for TMP."""
    stack: list[str] = []
    out_lines = []
    for line in text.split("\n"):
        units = _shape(_parse(line, stack))
        pieces = _wrap(units, max_em, metrics) if max_em else [units]
        for piece in pieces:
            out_lines.append(_emit(_reorder(_apply_marks(piece, marks))))
    if stack:
        raise ValueError(f"unclosed {stack} in {text!r}")
    return "\n".join(out_lines)
