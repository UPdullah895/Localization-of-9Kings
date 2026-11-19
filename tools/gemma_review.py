"""Ask the local Gemma (Ollama) to review Arabic translations for 9 Kings."""
import json, sys, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ar = json.loads((ROOT / "translations/ar.json").read_text(encoding="utf-8"))
en = json.loads((ROOT / "work/en.json").read_text(encoding="utf-8"))

SYSTEM = """أنت مراجع تعريب محترف للعبة 9 Kings (لعبة بناء رزم ودفاع عن البرج، ملك يضع بطاقات على قطع شبكة 5×5).
مهمتك: الحكم على كل ترجمة عربية مقابل النص الإنجليزي، وهل الصياغة عربية سليمة وطبيعية ودقيقة في سياق اللعبة.
معايير:
- فصحى حديثة واضحة، بلا عامية.
- النص الإنجليزي هو المصدر؛ لا تُضف معنى ولا تحذف معنى.
- {VAR1} و{VAR2} رموز تُستبدل بأرقام في اللعبة؛ يجب أن تبقى كما هي بالضبط، ويمكن تحريك موقعها.
- وسوم <color=...>...</color> تبقى كما هي.
- بعد {VAR1} يأتي الاسم مفردًا (قاعدة المشروع): "{VAR1} وحدة".
- المصطلحات الثابتة: plot=قطعة، troop=فرقة، unit=وحدة، building=مبنى، tome=كتاب، enchantment=تميمة، decree=مرسوم، perk=ميزة، blessing=بركة، gold=ذهب، life=روح، level=مستوى، stack=طبقة، damage=الضرر، health=الصحة، Warlock=المشعوذ، Wizard=الساحر، Poison Vial=قارورة السُّمّ.
- أسلوب الأساطير (Lore) كلاسيكي فخم.
أخرج لكل نص سطرًا واحدًا بهذا الشكل فقط:
TERM | ok
أو
TERM | EDIT: <الترجمة العربية المقترحة> | <سبب مختصر>
لا تكتب شيئًا آخر."""


def ask(pairs, model="gemma4:latest"):
    body = "\n".join(
        f"{i+1}) TERM: {k}\n   EN: {en[k]!r}\n   AR: {ar[k]!r}" for i, (k, _) in enumerate(pairs)
    )
    prompt = SYSTEM + "\n\nراجع هذه النصوص:\n\n" + body
    req = urllib.request.Request(
        "http://127.0.0.1:11434/api/chat",
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.15, "num_ctx": 16384},
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(r.read())["message"]["content"]


if __name__ == "__main__":
    keys = [k for k in json.loads(sys.stdin.read())]
    print(ask([(k, None) for k in keys]))
