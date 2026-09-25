"""Merge a batch of translations (JSON object on stdin) into translations/ar.json.

The batch is checked with check_translations.check first; nothing is written on
errors. Existing entries are replaced (that is how revisions are applied).

    merge_batch.py < batch.json
    merge_batch.py --todo PREFIX   print untranslated English terms starting with PREFIX
"""
import json
import sys
from pathlib import Path

import check_translations

ROOT = Path(__file__).resolve().parent.parent
AR = ROOT / "translations/ar.json"
EN = ROOT / "work/en.json"      # all English terms, dumped from original/data.unity3d


def main() -> int:
    english = json.loads(EN.read_text(encoding="utf-8"))
    arabic = json.loads(AR.read_text(encoding="utf-8"))
    if sys.argv[1:2] == ["--todo"]:
        prefix = sys.argv[2] if len(sys.argv) > 2 else ""
        for k, v in english.items():
            if k.startswith(prefix) and k not in arabic and not k.startswith("Format_"):
                print(json.dumps({k: v}, ensure_ascii=False)[1:-1])
        return 0
    batch = json.loads(sys.stdin.read())
    errors, warnings = check_translations.check(english, batch)
    for w in warnings:
        print("warning:", w)
    if errors:
        print("\n".join("ERROR: " + e for e in errors))
        return 1
    arabic.update(batch)
    AR.write_text(json.dumps(arabic, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"merged {len(batch)}; {len(arabic)}/{len(english)} translated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
