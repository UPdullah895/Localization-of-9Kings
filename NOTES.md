# 9 Kings — Arabic localization

Game: 9 Kings (Sad Socket), Steam appid 2784470, run under Proton.
Install: `~/.local/share/Steam/steamapps/common/9 Kings`

## Layout

- `original/` — pristine, read-only copies of game files (never edited; also the restore source)
- `translations/ar.json` — Arabic text, keyed by I2 term name
- `tools/` — `i2.py` (I2 asset reader/writer), `build.py`, `deploy.py`, inspection scripts
- `build/`, `work/` — generated; not in git
- `venv/` — UnityPy, TypeTreeGeneratorAPI, arabic-reshaper, python-bidi, addressablestools

## Engine facts (verified)

- Unity 6000.3.8f1, IL2CPP, metadata version 39. `TypeTreeGeneratorAPI` 0.0.10
  cannot load v39, so MonoBehaviours without type trees are read from raw bytes.
- Player log is disabled (`nolog=` in `boot.config`).

## Where the game's text lives

**I2 Localization**, not Unity Localization. All UI text is in one
`LanguageSourceAsset` named `I2Languages`: `data.unity3d` → `resources.assets`,
path_id 12310, ~3 MB, 1991 terms × 30 languages. The main menu uses
`MainMenu_Main_Start` ("START"), `MainMenu_Main_Options`, `MainMenu_Main_Extras`,
`MainMenu_Main_Quit`, etc.

The Unity Localization bundles in `StreamingAssets/aa` (111 entries, English
"Play" where the screen says "START") are not what the menu displays. The
September attempt edited those bundles, which is why nothing changed.

`tools/i2.py` parses the asset from raw bytes and rejects any layout that does
not re-serialize byte-identically. Field order: Term, TermType, Languages[],
Flags[], Languages_Touch[] per term; then LanguageData {Name, Code, Flags} list.

I2 ships its Arabic support (`RTLFixer`, `ApplyRTLfix`, `LanguagesRTL`), so
Arabic is stored unshaped, in logical order; I2 shapes and reorders it at
runtime for RTL languages. **Not yet confirmed in-game.**

The chosen language is saved in PlayerPrefs (Wine registry,
`pfx/user.reg` → `[Software\\SadSocket\\9Kings]`); nothing is saved until the
player changes language.

## Fonts

`LocalizationFonts` (resources.assets, path_id 12270) maps language names to a
font pair (normal, outlined):

| Languages | Font |
|---|---|
| default (anything unlisted) | EmptySans / EmptySans Outlined, fallback NotoSans / NotoSans Outlined |
| 16 Latin languages (English … Swedish) | TauSans / TauSans Outlined Bold |
| Japanese, Chinese (Simplified), Chinese (Traditional), Korean | matching NotoSans JP/SC/TC/KR |

Arabic is unlisted, so it gets the default chain; none of those fonts has
Arabic glyphs. The CJK Noto font assets are small and their TTFs are embedded
(5–10 MB `Font` objects), which points to dynamic TMP font assets.
**Open: how to add an Arabic font (next step after the language pipeline works).**

## Status

1. [x] Language pipeline built: `build.py` adds an `Arabic`/`ar` column (37
       main-menu/options terms translated, the rest copy English) and verifies
       only `I2Languages` changed.
2. [ ] In-game test: does Arabic appear in the language list, and does the menu
       switch to it (expect empty boxes until the font step)?
3. [ ] Arabic font.
4. [ ] Confirm I2's runtime shaping/RTL output looks right.

## Commands

```bash
./venv/bin/python tools/build.py            # build/data.unity3d
./venv/bin/python tools/deploy.py install   # game must be closed
./venv/bin/python tools/deploy.py restore
./venv/bin/python tools/deploy.py status
```
