import json
from pathlib import Path

files = [
    "dataset/legal_cases.json",
    "dataset/nyaysaathi_200plus.json",
    "dataset/synthetic_multilingual_training.json",
    "nyaysaathi_with_descriptions.json",
    "nyaysaathi_hindi.json",
    "nyaysaathi_marathi.json",
    "nyaysaathi_part1.json",
    "nyaysaathi_part2.json",
    "nyaysaathi_part3.json",
]

for path in files:
    p = Path(path)
    if not p.exists():
        print(f"MISSING: {path}")
        continue
    try:
        data = json.load(open(p, "r", encoding="utf-8"))
        if isinstance(data, list):
            print(f"{path}: {len(data)} records")
            cats = {}
            for item in data:
                cat = item.get("category", "Unknown")
                cats[cat] = cats.get(cat, 0) + 1
            if cats:
                print("  Categories:")
                for k, v in sorted(cats.items(), key=lambda x: x[0].lower()):
                    print(f"    {k}: {v}")
        else:
            print(f"{path}: not a list ({type(data).__name__})")
    except Exception as e:
        print(f"{path}: ERROR {e}")