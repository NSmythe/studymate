"""
Compares the AI judge sheet (rating_sheets/R1_ai_reference.docx) with the human
ratings in rating_sheets/ratings.csv. Items are matched by text because item IDs
are shuffled differently on each sheet. The AI ratings are never mixed into the
human averages.

Usage:
    python3 score_ratings.py      # human ratings -> ratings.csv
    python3 compare_ai_judge.py
"""
import csv, os
from collections import defaultdict
from statistics import mean
from score_ratings import parse_sheet, DIR

AI_SHEET, AI_RATER = os.path.join(DIR, "R1_ai_reference.docx"), "R1"
SUMM, QUIZ = ("coverage", "accuracy", "readability"), ("accurate", "relevant", "no_clues")
METHODS = {"summary": ("studymate", "lead_n_baseline", "t5_small"), "quiz": ("studymate", "lead_n_baseline")}

key = {r["item_id"]: r for r in csv.DictReader(open(os.path.join(DIR, "key_PRIVATE.csv"))) if r["rater"] == AI_RATER}
ai = [{**key[i], **v} for i, v in parse_sheet(AI_SHEET).items()]
human = list(csv.DictReader(open(os.path.join(DIR, "ratings.csv"))))
by_text = defaultdict(list)
for h in human:
    by_text[h["text"]].append(h)
assert all(by_text[a["text"]] for a in ai), "some AI items have no human match"

print(f"AI judge vs. humans ({', '.join(sorted({h['rater'] for h in human}))}) | {len(ai)} items matched by text\n")
print("SUMMARIES: mean score (1-5), AI vs. human")
print(f"{'Method':<18}" + "".join(f"{f.title() + ' AI/Hum':<22}" for f in SUMM))
for m in METHODS["summary"]:
    a = [x for x in ai if x["type"] == "summary" and x["method"] == m]
    h = [y for y in human if y["type"] == "summary" and y["method"] == m]
    print(f"{m:<18}" + "".join(f"{mean(x[f] for x in a):.2f} / {mean(int(y[f]) for y in h):<14.2f}" for f in SUMM))

print("\nQUIZ QUESTIONS: share rated Y, AI vs. human")
print(f"{'Method':<18}" + "".join(f"{f.title() + ' AI/Hum':<22}" for f in QUIZ))
for m in METHODS["quiz"]:
    a = [x for x in ai if x["type"] == "quiz" and x["method"] == m]
    h = [y for y in human if y["type"] == "quiz" and y["method"] == m]
    print(f"{m:<18}" + "".join(f"{mean(x[f] == 'Y' for x in a):.2f} / {mean(y[f] == 'Y' for y in h):<14.2f}" for f in QUIZ))

print("\nAGREEMENT with human majority (duplicate questions share one human majority)")
for f in QUIZ:
    q = [x for x in ai if x["type"] == "quiz"]
    maj = [mean(y[f] == "Y" for y in by_text[x["text"]]) for x in q]
    ok = sum((x[f] == "Y") == (v >= 0.5) for x, v in zip(q, maj) if v != 0.5)
    n = sum(v != 0.5 for v in maj)
    print(f"  quiz {f:<12} {ok}/{n} = {ok / n:.2f}  (ties excluded)")
for f in SUMM:
    s = [x for x in ai if x["type"] == "summary"]
    gaps = [abs(x[f] - mean(int(y[f]) for y in by_text[x["text"]])) for x in s]
    print(f"  summary {f:<12} mean gap {mean(gaps):.2f} pts; within 1 pt: {sum(g <= 1 for g in gaps)}/{len(gaps)}")
