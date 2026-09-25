# 9 Kings — Arabic glossary and style guide

Read this before translating or reviewing any string. Consistency matters more
than any single clever rendering: a card name must read the same on the card,
in every description that mentions it, and in the achievements.

## The game, briefly

A roguelike deck-builder with tower defence. You are one of nine kings. Each
year (a turn) you place cards from your hand onto **plots** of a 5×5 kingdom
grid: troops, buildings, towers, and tomes/enchantments that modify plots.
Placing a matching card on a plot levels it up. A battle starts when two cards
remain in your hand; enemies march at your base and you lose a life if they
reach it. Between battles come events: merchants, the Royal Council (decrees),
the diplomat (war/peace), the prophet (a blessing in 9 years). Survive the
years to win. Perks are unlocked by levelling a king and slotted on a grid
before a run. Quest Mode has 81 authored scenarios; Multiplayer ("Royale")
pits nine real players against each other.

## Voice and register

- UI, card text, rules: clear Modern Standard Arabic, short, imperative for
  instructions ("اسحب", "ارمِ"). Rules text must be unambiguous: a player makes
  decisions from it.
- Humour and puns (achievements, skins, flavour): recreate the joke in Arabic;
  never translate a pun literally into nonsense. A different Arabic joke that
  lands is better than a faithful one that doesn't.
- Lore (`Lore_*`, archaic English): classical, elevated Arabic with the
  rhythm of old chronicles (أما، إذ، لَعَمْري، هيهات، فويلٌ لمن...).
- Quest advisor lines (`Challenge_*_Desc`) keep each kingdom's advisor voice:

| Kingdom | Advisor voice in English | Arabic rendering |
|---|---|---|
| Blood | cackling, sinister, "Khehehehe", "Your Unholiness/Malignance/Evilness" | شرير متهكم، ضحكة «خِهِهِهِه»، «يا صاحب الدناسة/الخبث/الشر» |
| Greed | money-obsessed courtier, "Milord", "boss" | متملق مهووس بالمال، «مولاي»، «يا زعيم» |
| Nature | caveman grammar, emoticons `>:|` | عربية مكسّرة بلا أدوات ربط تقريبًا، مع الوجوه `>:|` كما هي |
| Nomads | haiku, 3 lines | ثلاثة أسطر قصيرة موزونة الإيقاع قدر الإمكان |
| Nothing | dry, deadpan | جاف، ساخر ببرود |
| Progress | tech-bro, "MOAR" | متحمس للتقنية، «المزيييد!» |
| Spells | pompous, insults others' intellect | متعالٍ متحذلق يحتقر عقول الآخرين |
| Stone | ALL CAPS, words... separated... by... pauses | كلمات... متقطعة... بنقاط... (لا توجد أحرف كبيرة في العربية؛ التقطيع هو الصوت) |
| Time | "Tick. Tock." | «تِك. تَك.» |

## Technical rules (the build checks these)

- Keep every placeholder exactly: `{VAR1}`, `{VAR2}`, `{VAR}`, `{KING}`,
  `{YEAR}`, `{DIFFICULTY}`, `{KINGCOLOR}`. Move it within the sentence as Arabic
  word order needs. `{VAR1}` often carries its own sign/percent (e.g. "+50%"),
  so don't add "+" or "%" around it unless the English does.
- Keep rich-text tags exactly and balanced: `<color=...>…</color>`, `<size=..>…</size>`.
- Keep `\n` line breaks where the layout needs them (titles split over two lines).
- `Format_*` terms are .NET number formats: never translate them.
- Game title "9 Kings", emails and URLs stay in Latin script.
- Numbers after a noun count: use the singular noun after the placeholder
  ("{VAR1} وحدة", "{VAR1} ذهب"); the value is unknown, so plural agreement can't be chosen.
- Humour stays in Modern Standard Arabic; no dialect words (برضو، مش، لازم),
  except where broken grammar is the character's voice (Nature advisor).
- Stat labels the game completes with a number ("Health: " + value) are laid out
  left-to-right by the build ("الصحة: 50"); keep them as a label ending in a colon.
- Digits: Western digits (0-9), matching the numbers the game inserts.
- Diacritics (tashkeel): only where needed to prevent a misreading
  (مُلك/مَلِك، الرُّحَّل، استُخدم) or for tanween fath on adverbs (حقًّا، أيضًا). Not full
  vocalisation. The build places each letter's marks with the font's own anchors
  (visual.py), so any combination renders, including shadda with a vowel.
- Verbs: intransitive when the subject changes by itself ("Levels up target plot"
  → يرتفع مستوى القطعة, not يرفع).

## Terms

### Kings and factions

| English | Arabic | Notes |
|---|---|---|
| King of Nothing | ملك اللاشيء | keeps the "Nothing" puns working (اللاشيء يكفي) |
| King of Spells | ملك التعاويذ | |
| King of Blood | ملك الدم | |
| King of Greed | ملك الجشع | |
| King of Nature | ملك الطبيعة | |
| King of Progress | ملك التقدّم | |
| King of Nomads | ملك الرُّحَّل | |
| King of Stone | ملك الحجر | |
| King of Time | ملك الزمن | `King_Kings` = Time |
| Jack of Rainbows | صاحب قوس قزح | "Jack of all trades" idiom → صاحب الصنائع |
| Jack of Chaos | صاحب الفوضى | |
| Jack of Structures / Magic / Arms / All Trades | صاحب البُنى / صاحب السحر / صاحب السلاح / صاحب كل الصنائع | merchants |
| Joker | الجوكر | |
| Rebellion (e.g. Blood Rebellion) | تمرّد (تمرّد الدم) | |
| Champion of X | بطل X (بطل الدم) | |
| Nothing/Spells/... (short faction labels) | اللاشيء / التعاويذ / الدم / الجشع / الطبيعة / الرُّحَّل / الحجر / التقدّم / الزمن | |

### Core mechanics

| English | Arabic | Notes |
|---|---|---|
| plot | قطعة (ج. قطع) | a tile of the kingdom grid |
| kingdom | مملكة | |
| card / hand / deck | بطاقة / يد / رزمة | |
| the Pit / throw into the pit | الحفرة / ارمِ في الحفرة | discards a card for gold |
| base | القاعدة | card type; the castle plot |
| troop | فرقة (ج. فرق) | a troop card/plot; its soldiers are units |
| unit | وحدة (ج. وحدات) | |
| building / construction | مبنى / منشأة | |
| tower | برج | |
| tome | كتاب (ج. كتب) | card type; "destruction tomes" = كتب الهدم |
| enchantment | تميمة (ج. تمائم) | card type; charms attached to units in stacks. Not طلسم: rare, reads as "cipher" |
| trash | خردة | card type |
| spell (generic) | تعويذة | |
| summon | مُستدعى / يستدعي | |
| level / level up / max level | مستوى / يرتقي مستوى / أقصى مستوى | |
| stats / all stats | الخصائص / جميع الخصائص | |
| damage | الضرر | |
| HP | الصحة | "HP" as a label → الصحة |
| attack speed / movement speed | سرعة الهجوم / سرعة الحركة | |
| hits/second | ضربة/ثانية | |
| critical chance / critical damage | فرصة الضربة الحرجة / الضرر الحرج | |
| AoE / area damage | ضرر منطقة / نطاق الأثر | |
| range | المدى | |
| stack (of poison, enchantment) | طبقة (ج. طبقات) | |
| poison / frozen / stunned | سُمّ / مُجمَّد / مصعوق | |
| gold | ذهب | |
| life / lives | روح / أرواح | |
| year | عام | the game's turn; "YEAR 12" → العام 12 |
| re-roll | تجديد (ج. تجديدات) | refreshing offers/enemies |
| decree / Royal Council | مرسوم (ج. مراسيم) / المجلس الملكي | `Policy_*` are decrees |
| perk | ميزة (ج. مزايا) | |
| blessing / prophet / prophecy | بركة / العرّاف / النبوءة | avoid religious نبي |
| merchant | التاجر | |
| diplomat / war / peace | السفير / حرب / سلام | |
| loot / chest / treasure chest | غنيمة / صندوق / صندوق كنز | |
| rainbow card | بطاقة قوس قزح | rare cards |
| chaos | الفوضى | |
| razed / destroyed | مُدمَّرة / تُهدَم | |
| unlock (plot) / locked | يفتح / مُقفلة | |
| Expansion Tower / expansion mode | برج التوسّع / وضع التوسّع | |
| Endless Mode | الطور اللانهائي | |
| Quest Mode / quest | طور المهام / مهمة | |
| Multiplayer / Royale | اللعب الجماعي / المعركة الملكية | |
| medals / rank points | أوسمة / نقاط التصنيف | |
| run (one playthrough) | جولة | |
| quest / Quest Mode | مهمة / طور المهام | single-player authored scenarios |
| mission (daily, multiplayer) | هدف يومي / الأهداف اليومية | kept apart from quests (مهمة) |
| game mode (Endless, Quest, Speed) | طور | UI states (expansion mode, stats mode) use وضع |
| Single Player / Multiplayer | لعب فردي / لعب جماعي | main menu pair |

### Units and buildings that are easy to confuse

| English | Arabic | Why |
|---|---|---|
| Ogre / Meat Troll | الغول / ترول اللحم | both were غول at first |
| Raptor | الرابتور (ج. رابتورات) | the dinosaur, not جارح (bird of prey) |
| Ballista | العرّادة | the classical Arabic siege weapon |
| Castle / Citadel / Stronghold / Bastion | القلعة / الحصن / المعقل / الصرح | four fortifications, four distinct words |
| Warper / Orbiter | طاوي المكان / الدوّار | from طيّ المكان; "orbits" its neighbours |
| Recycler | مُعيد التدوير | المُعيد alone was unclear |

### Difficulties

Peasant فلاح · Squire تابع · Knight فارس · Lord سيّد · Baron بارون ·
Count كونت · Duke دوق · Prince أمير · King ملك (King II… → ملك II…, keep Roman numerals).

### Forms of address

Milord / my liege → مولاي · Your Highness / Your Grace → صاحب الجلالة / يا صاحب
الجلالة · Your Unholiness → يا صاحب الدناسة · Your Malignance → يا صاحب الخبث ·
Your Evilness → يا صاحب الشر.
