# How the translation works

Notes for anyone working on the mod rather than playing with it. For installing it, see
the [README](../README.md). For how the *translation* itself is made — terminology,
voice, what gets recreated rather than translated — see [METHOD.md](METHOD.md).

## Working on it

Building needs a copy of the game's own `9Kings_Data/data.unity3d` (version 0.9.6.5) at
`original/data.unity3d`. It is not in this repo and never will be.

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
```

```bash
./venv/bin/python tools/build.py                     # build/data.unity3d + installer/payload/
./venv/bin/python -m unittest discover tests
./venv/bin/python tools/preview.py TERM ...          # work/preview.png, drawn like the game
./venv/bin/python tools/merge_batch.py < batch.json  # add or revise translations
./venv/bin/python tools/deploy.py install            # into the real game; it must be closed
./venv/bin/python tools/deploy.py restore
./venv/bin/python installer/package.py               # dist/9Kings-Arabic(.exe)
```

Translations live in `translations/ar.json`, keyed by I2 term name and written in normal
logical order. GitHub Actions builds the Windows and Linux installers; tagging `v*`
publishes a release.

## Where the text lives

**I2 Localization**, not Unity Localization. Every string the UI draws is in one
`LanguageSourceAsset` named `I2Languages` — `data.unity3d` → `resources.assets`, path_id
12310, about 3 MB, 1,991 terms × 30 languages.

The Unity Localization bundles under `StreamingAssets/aa` are a decoy: they hold 111
entries and say "Play" where the screen says "START". Editing them changes nothing.

Engine facts behind that, all verified rather than assumed: Unity 6000.3.8f1, IL2CPP,
metadata version 39. `TypeTreeGeneratorAPI` 0.0.10 cannot load v39, so MonoBehaviours
without type trees are read from raw bytes — which is what `tools/i2.py` does. It rejects
any layout that does not re-serialize byte-identically. The field order per term is
`Term, TermType, Languages[], Flags[], Languages_Touch[]`, then a `LanguageData
{Name, Code, Flags}` list. The player log is disabled (`nolog=` in `boot.config`), so
there is nothing to read when something goes wrong; the byte check is the safety net.

## How it works

**1. The language column.** A new column is added to `I2Languages` under the code
`ar-001`. I2 *ships* an Arabic right-to-left fix (`RTLFixer`), but in this game it garbles
the text: it wraps a reversed paragraph so the lines run bottom-to-top, it splits
`<color=#{KINGCOLOR}>` at the inner brace, it swaps `{VAR1}` and `{VAR2}`, and it
misplaces harakat — all seen in-game. `ar-001` is not in I2's RTL list, so the fix never
runs and `tools/visual.py` stores every string already shaped, reordered and wrapped.

**2. The font.** `LocalizationFonts` (path_id 12270) maps a language to a font pair. The
16 Latin languages get TauSans and the CJK languages get matching Noto faces; anything
unlisted — Arabic included — falls through to EmptySans → NotoSans. Both NotoSans assets
are **dynamic** TMP assets referencing the embedded `Font` "NotoSans-Medium"
(path_id 923, a 631 KB TTF), and TMP rasterises missing glyphs from it at runtime. So
`tools/font_merge.py` merges `fonts/NotoSansArabic-Medium.ttf` into that TTF, keeps the
game font's metrics and name tables, and verifies that all 3,094 original codepoints still
draw identically and all 1,171 added Arabic ones match Noto Sans Arabic. Noto Sans Arabic
maps every presentation form (FB50–FDFF, FE70–FEFC), which is exactly what the shaper
emits, so no extra cmap work is needed.

**3. Shaping and direction.** `tools/visual.py` reshapes to presentation forms and emits
**visual order** at build time, with a bidi pass that leaves game values such as `+50%`
intact and does not disturb colour tags or placeholders.

**4. Harakat.** TMP has no GPOS mark positioning, so a naive diacritic lands in the wrong
place. Each letter's marks are instead baked into one zero-width Private Use Area glyph,
positioned from Noto Sans Arabic's own GPOS anchors for that letter form
(`visual.MarkGlyphs`, `font_merge.add_marks`).

**5. The patch.** `tools/patch.py` is the patch itself, shared by the build and the
installer. It checks that only the two intended objects changed and that both read back
exactly. The installer ships only the translated strings, the harakat glyph spec and the
font — it patches the player's own game file and keeps a verified backup of the original.

The chosen language is saved in PlayerPrefs (under Wine, `pfx/user.reg` →
`[Software\SadSocket\9Kings]`), and nothing is written there until the player changes
language for the first time.

## Layout

`translations/layout.json` sets the line width each term is wrapped to, because the
stored text is already in visual order and letting the engine re-wrap it is what inverts
the line order. Wrapping narrower than the box is always safe; wrapping wider is not.

`tools/preview.py` draws a stored string the way the engine does, which is the fastest way
to check a width without launching the game. `tests/test_visual.py` locks in every display
bug found so far, so a fix cannot silently regress.

## Checking

`tools/check_translations.py` runs as part of the build and refuses to let a string
through if it drops or adds a placeholder or a colour tag, or if it touches one of the
number formats. On top of that the patch verifies its own bytes, and the font merge
verifies every glyph on both sides of the merge.

## State

1,985 of 1,991 terms are translated. The six left alone are `Format_*` number formats,
which are not text. Box widths in `layout.json` are measured as screens are reviewed; an
unreviewed panel may still wrap wrongly, and that is the thing to look for first when
something looks out of order.
