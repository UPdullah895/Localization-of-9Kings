"""Read and write the I2 Localization `I2Languages` asset (LanguageSourceAsset).

The game is IL2CPP (metadata v39), and no available type-tree generator reads
that version yet, so this module parses the MonoBehaviour's raw bytes with the
field layout of I2's LanguageSourceData. The layout is correct only if
`parse()` consumes every byte and `serialize(parse(raw)) == raw`; `load()`
checks both, so a layout mistake fails loudly instead of corrupting the asset.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field


class _Reader:
    def __init__(self, data: bytes):
        self.d, self.p = data, 0

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def f32(self) -> float:
        v = struct.unpack_from("<f", self.d, self.p)[0]
        self.p += 4
        return v

    def raw(self, n: int) -> bytes:
        v = self.d[self.p:self.p + n]
        if len(v) != n:
            raise ValueError(f"truncated read of {n} bytes at {self.p}")
        self.p += n
        return v

    def align(self) -> None:
        self.p = (self.p + 3) & ~3

    def string(self) -> str:
        v = self.raw(self.u32()).decode("utf-8")
        self.align()
        return v

    def byte_array(self) -> bytes:
        v = self.raw(self.u32())
        self.align()
        return v

    def string_array(self) -> list[str]:
        return [self.string() for _ in range(self.u32())]


class _Writer:
    def __init__(self):
        self.b = bytearray()

    def u32(self, v: int) -> None:
        self.b += struct.pack("<I", v)

    def f32(self, v: float) -> None:
        self.b += struct.pack("<f", v)

    def align(self) -> None:
        self.b += b"\0" * (-len(self.b) % 4)

    def string(self, s: str) -> None:
        e = s.encode("utf-8")
        self.u32(len(e))
        self.b += e
        self.align()

    def byte_array(self, v: bytes) -> None:
        self.u32(len(v))
        self.b += v
        self.align()

    def string_array(self, v: list[str]) -> None:
        self.u32(len(v))
        for s in v:
            self.string(s)


@dataclass
class Term:
    name: str
    type: int                 # I2 eTermType; 0 = Text
    languages: list[str]      # one entry per LanguageSource.languages, same order
    flags: bytes              # one byte per language
    languages_touch: list[str] = field(default_factory=list)


@dataclass
class Language:
    name: str
    code: str
    flags: int


@dataclass
class LanguageSource:
    header: bytes             # MonoBehaviour base: m_GameObject, m_Enabled, m_Script
    asset_name: str
    agreement_flags: list[int]            # UserAgreesToHaveItOnTheScene, ...InsideThePluginsFolder, GoogleLiveSyncIsUptoDate
    terms: list[Term]
    case_insensitive_terms: int
    on_missing_translation: int
    term_app_name: str
    languages: list[Language]
    ignore_device_language: int
    allow_unloading_languages: int
    google: list[str]                     # WebServiceURL, SpreadsheetKey, SpreadsheetName, LastUpdatedVersion
    google_ints: list[int]                # UpdateFrequency, InEditorCheckFrequency, UpdateSynchronization
    google_update_delay: float
    assets: bytes                         # List<Object>: count + PPtrs, kept verbatim

    def term(self, name: str) -> Term:
        return next(t for t in self.terms if t.name == name)

    def lang_index(self, code: str) -> int:
        return next(i for i, l in enumerate(self.languages) if l.code == code)

    def add_language(self, name: str, code: str, fill_from: str | None = None) -> int:
        """Append a language column; each term's new cell copies `fill_from` or is empty."""
        if any(l.code == code for l in self.languages):
            raise ValueError(f"language {code} already present")
        src = self.lang_index(fill_from) if fill_from else None
        self.languages.append(Language(name, code, 0))
        for t in self.terms:
            t.languages.append(t.languages[src] if src is not None else "")
            t.flags = t.flags + b"\0"
        return len(self.languages) - 1


HEADER_SIZE = 12 + 4 + 12  # PPtr m_GameObject, bool m_Enabled (aligned), PPtr m_Script


def parse(raw: bytes) -> LanguageSource:
    r = _Reader(raw)
    header = r.raw(HEADER_SIZE)
    asset_name = r.string()
    agreement = [r.u32() for _ in range(3)]
    terms = []
    for _ in range(r.u32()):
        name = r.string()
        ttype = r.u32()
        langs = r.string_array()
        flags = r.byte_array()
        touch = r.string_array()
        terms.append(Term(name, ttype, langs, flags, touch))
    case_ins = r.u32()
    on_missing = r.u32()
    app_name = r.string()
    languages = []
    for _ in range(r.u32()):
        lname = r.string()
        code = r.string()
        lflags = r.raw(1)[0]
        r.align()
        languages.append(Language(lname, code, lflags))
    ignore_dev = r.u32()
    allow_unload = r.u32()
    google = [r.string() for _ in range(4)]
    google_ints = [r.u32() for _ in range(3)]
    delay = r.f32()
    assets_start = r.p
    n_assets = r.u32()
    r.raw(n_assets * 12)
    assets = raw[assets_start:r.p]
    if r.p != len(raw):
        raise ValueError(f"layout mismatch: parsed {r.p} of {len(raw)} bytes")
    return LanguageSource(header, asset_name, agreement, terms, case_ins, on_missing, app_name,
                          languages, ignore_dev, allow_unload, google, google_ints, delay, assets)


def serialize(src: LanguageSource) -> bytes:
    n = len(src.languages)
    w = _Writer()
    w.b += src.header
    w.string(src.asset_name)
    for v in src.agreement_flags:
        w.u32(v)
    w.u32(len(src.terms))
    for t in src.terms:
        if len(t.languages) != n or len(t.flags) != n:
            raise ValueError(f"term {t.name!r} has {len(t.languages)} cells for {n} languages")
        w.string(t.name)
        w.u32(t.type)
        w.string_array(t.languages)
        w.byte_array(t.flags)
        w.string_array(t.languages_touch)
    w.u32(src.case_insensitive_terms)
    w.u32(src.on_missing_translation)
    w.string(src.term_app_name)
    w.u32(n)
    for l in src.languages:
        w.string(l.name)
        w.string(l.code)
        w.b.append(l.flags)
        w.align()
    w.u32(src.ignore_device_language)
    w.u32(src.allow_unloading_languages)
    for s in src.google:
        w.string(s)
    for v in src.google_ints:
        w.u32(v)
    w.f32(src.google_update_delay)
    w.b += src.assets
    return bytes(w.b)


def load(raw: bytes) -> LanguageSource:
    """Parse and verify the layout by requiring a byte-identical round trip."""
    src = parse(raw)
    if serialize(src) != raw:
        raise ValueError("round-trip mismatch: field layout is wrong for this asset")
    return src
