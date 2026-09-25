# تعريب 9 Kings — Localization of 9 Kings

تعريب كامل وغير رسمي للعبة [9 Kings](https://store.steampowered.com/app/2784470/9_Kings/)

An unofficial, complete Arabic localization of **9 Kings**

| | |
|---|---|
| إصدار اللعبة المدعوم / Supported game version | **0.9.6.5** (Steam build 25462185) |
| النصوص المترجمة / Texts translated | 1985 of 1991 (the other 6 are number formats) |
| الخط / Font | Noto Sans Arabic Medium (SIL OFL 1.1) |

---

## بالعربية

### التثبيت

1. حمّل المثبّت من صفحة [Releases](../../releases):
   - ويندوز: `9Kings-Arabic-Windows.exe`
   - لينكس: `9Kings-Arabic-Linux` (ثم `chmod +x 9Kings-Arabic-Linux`)
2. أغلق اللعبة، ثم شغّل المثبّت.
3. يبحث المثبّت تلقائيًا عن اللعبة في مكتبات Steam. إن لم يجدها، اكتب مسار مجلد اللعبة أو اسحبه إلى النافذة
   (في Steam: زر الفأرة الأيمن على 9 Kings ← إدارة ← تصفّح الملفات المحلية).
4. اختر «Install»، ثم شغّل اللعبة واختر من الإعدادات ← اللغة: **Arabic**.

### إلغاء التثبيت

شغّل المثبّت نفسه واختر «Uninstall»، فيُعيد الملف الأصلي من النسخة الاحتياطية بعد التحقق منها.
ويمكنك دائمًا استعادة اللعبة من Steam: خصائص ← الملفات المثبّتة ← التحقق من سلامة ملفات اللعبة.

### ملاحظات

- المثبّت لا يحمل أي ملفات من اللعبة؛ بل يعدّل نسختك أنت، ويحتفظ بنسخة احتياطية من الملف الأصلي.
- يعمل التعريب مع الإصدار 0.9.6.5 فقط. إذا حُدّثت اللعبة فلن يعدّل المثبّت شيئًا، وسيطلب منك انتظار إصدار جديد من التعريب.
- اعتمدت الترجمة على قراءة نصوص اللعبة كاملة وفهم سياقها، لا على الترجمة الحرفية. المصطلحات موثّقة في [docs/glossary.md](docs/glossary.md).

---

## English

### Install

1. Download the installer from [Releases](../../releases): `9Kings-Arabic-Windows.exe` or `9Kings-Arabic-Linux`.
2. Close the game and run the installer. It finds 9 Kings in your Steam libraries, or asks for the game folder.
3. Choose Install, start the game, and pick **Arabic** under Settings > Language.

Run the installer again to uninstall: it verifies the backup and restores the original file.
Steam's "Verify integrity of game files" also restores the game.

### How it works

The game's UI text is in I2 Localization (`I2Languages` in `data.unity3d`), drawn by TextMesh Pro,
which has no Arabic shaping or bidi. I2's own right-to-left fix garbles this game's text (reversed
wrapped lines, broken colour tags, swapped placeholders), so the Arabic column is added under
code `ar-001` and every string is stored ready to draw:

- `tools/visual.py`: shaping to presentation forms, a bidi reorder that keeps game values such as
  `+50%` intact, build-time line wrapping from font metrics, and harakat placed from Noto Sans
  Arabic's GPOS anchors as precomposed glyphs.
- `tools/font_merge.py`: merges Noto Sans Arabic into the game's NotoSans fallback font.
- `tools/patch.py`: the patch itself, shared by the build and the installer. It checks that only
  the two intended objects changed and that both read back exactly.

The installer ships only the translated strings, the harakat glyph spec and the font; it patches
the player's own game file.

### Building

Needs a copy of the game's `9Kings_Data/data.unity3d` (version 0.9.6.5) at `original/data.unity3d`.

```bash
python -m venv venv && venv/bin/pip install -r requirements.txt
venv/bin/python tools/build.py            # installer/payload/ and build/data.unity3d
venv/bin/python -m unittest discover tests
venv/bin/python installer/package.py      # dist/9Kings-Arabic(.exe)
```

Translations live in `translations/ar.json`, written in normal logical order.
`translations/layout.json` sets line widths. The method and references are in [docs/METHOD.md](docs/METHOD.md).
GitHub Actions builds the Windows and Linux installers; tagging `v*` publishes a release.

### Credits

- **9 Kings** © Sad Socket. This project is not affiliated with or endorsed by Sad Socket or Hooded Horse,
  and contains no game files.
- Noto Sans Arabic © The Noto Project Authors, [SIL Open Font License 1.1](fonts/OFL.txt).
