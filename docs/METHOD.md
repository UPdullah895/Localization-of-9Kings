# How this translation is made

## Process

1. **Read everything first.** All 1,991 English strings were read before translating,
   to learn the game's systems (plots, troops, tomes, decrees, blessings), which
   strings are UI and which are flavour, and who is speaking in each.
2. **Terminology before translation.** `docs/glossary.md` fixes one Arabic term per
   game concept. A card name must read the same on the card, in every description
   that mentions it, and in achievements; players make decisions from rules text.
3. **Translate meaning, not words.** Rules text is short, unambiguous Modern Standard
   Arabic. Jokes and puns are recreated, not translated literally (an achievement
   title that makes an Arabic player smile beats a faithful one that doesn't).
   Each quest advisor keeps a voice (the glossary's voice table).
4. **Machine checks** (`tools/check_translations.py`, run by the build): every
   placeholder and colour tag of the English survives; number formats are untouched.
5. **Rendering checks.** `tools/preview.py` draws the stored text the way the game
   engine does; `tests/test_visual.py` locks in every display bug found so far.
6. **In-game review** of each screen, then a consistency pass over the whole file
   (e.g. two units both called غول, a raptor translated as a bird of prey).

## Further reading

- Minako O'Hagan & Carmen Mangiron, *Game Localization: Translating for the Global
  Digital Entertainment Industry* (John Benjamins, 2013): the standard academic survey,
  including "transcreation", the freedom games need to recreate humour and tone.
- Miguel Á. Bernal-Merino, *Translation and Localisation in Video Games: Making
  Entertainment Software Global* (Routledge, 2015): text types in games (UI, rules,
  narrative, lore) and how each is translated differently.
- Heather Maxwell Chandler & Stephanie O'Malley Deming, *The Game Localization
  Handbook* (2nd ed., 2011): the production side (glossaries, context, testing).
- IGDA Localization SIG, *Best Practices for Game Localization*: a short, free guide
  written for developers and translators.
- Microsoft's Arabic localization style guide (Microsoft Language Portal / Style
  Guides): concrete conventions for Arabic UI text: tone, punctuation, numbers.
- Unicode Standard Annex #9, *Unicode Bidirectional Algorithm*: how right-to-left
  and left-to-right text mix; the basis of `tools/visual.py`.
