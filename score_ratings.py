"""
Scores filled-in human review sheets.

Reads each rating_sheets/R*_filled.docx, matches every item ID to its method
using rating_sheets/key_PRIVATE.csv, saves all scores to
rating_sheets/ratings.csv, and prints per-method averages. If more than one
rater is present, it also lists items where raters disagree.

Usage:
    python3 score_ratings.py
"""

import csv
import glob
import os
import re
import subprocess
from collections import defaultdict
from statistics import mean

DIR = "rating_sheets"
HEADERS = {"Coverage (1-5)", "Accuracy (1-5)", "Readability (1-5)", "Comments", "ID", "Question",
           "Answer", "Accurate (Y/N)", "Relevant (Y/N)", "No clues (Y/N)", "Quiz questions", "Summaries"}
SUMMARY_ID = re.compile(r"^Summary (T\d-S[A-Z])$")
QUIZ_ID = re.compile(r"^(T\d-Q\d+)$")


def docx_lines(path):
    text = subprocess.run(["textutil", "-convert", "txt", "-stdout", path],
                          capture_output=True, text=True, check=True).stdout
    return [line.strip() for line in text.splitlines() if line.strip()]


def is_boundary(line):
    return bool(SUMMARY_ID.match(line) or QUIZ_ID.match(line) or line.startswith("Topic ")
                or line in ("Quiz questions", "Summaries"))


def parse_sheet(path):
    lines = docx_lines(path)
    items = {}
    i = 0
    while i < len(lines):
        s = SUMMARY_ID.match(lines[i])
        q = QUIZ_ID.match(lines[i])
        if s:
            j = i + 2  # skip summary text
            while j < len(lines) and lines[j] in HEADERS:
                j += 1
            nums = lines[j:j + 3]
            if not all(n.isdigit() for n in nums):
                raise ValueError(f"{path}: {s.group(1)} is missing a 1-5 score: {nums}")
            j += 3
            comment = lines[j] if j < len(lines) and not is_boundary(lines[j]) else ""
            items[s.group(1)] = {"text": lines[i + 1], "coverage": int(nums[0]), "accuracy": int(nums[1]),
                                 "readability": int(nums[2]), "comments": comment}
            i = j
        elif q:
            yn = [v.upper() for v in lines[i + 3:i + 6]]
            if not all(v in ("Y", "N") for v in yn):
                raise ValueError(f"{path}: {q.group(1)} is missing a Y/N rating: {yn}")
            j = i + 6
            comment = lines[j] if j < len(lines) and not is_boundary(lines[j]) else ""
            items[q.group(1)] = {"text": lines[i + 1] + " || " + lines[i + 2], "accurate": yn[0], "relevant": yn[1], "no_clues": yn[2], "comments": comment}
            i = j
        else:
            i += 1
    return items


def main():
    key = {(r["rater"], r["item_id"]): r for r in csv.DictReader(open(os.path.join(DIR, "key_PRIVATE.csv")))}
    rows = []
    for path in sorted(glob.glob(os.path.join(DIR, "R*_filled.docx"))):
        rater = os.path.basename(path).split("_")[0]
        items = parse_sheet(path)
        expected = [k[1] for k in key if k[0] == rater]
        missing = [i for i in expected if i not in items]
        if missing:
            raise ValueError(f"{path}: no ratings found for {missing}")
        for item_id in expected:
            k = key[(rater, item_id)]
            rows.append({"rater": rater, "item_id": item_id, "case": k["case"], "type": k["type"],
                         "method": k["method"], **items[item_id]})

    fields = ["rater", "item_id", "case", "type", "method", "coverage", "accuracy", "readability",
              "accurate", "relevant", "no_clues", "comments", "text"]
    with open(os.path.join(DIR, "ratings.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    raters = sorted({r["rater"] for r in rows})
    print(f"Raters: {', '.join(raters)} | items rated: {len(rows)}\n")

    print("SUMMARIES: mean score (1-5), n = summaries rated")
    print(f"{'Method':<18}{'n':<5}{'Coverage':<10}{'Accuracy':<10}{'Readability':<12}")
    summ = defaultdict(list)
    for r in rows:
        if r["type"] == "summary":
            summ[r["method"]].append(r)
    for m in ("studymate", "lead_n_baseline", "t5_small"):
        g = summ[m]
        print(f"{m:<18}{len(g):<5}{mean(x['coverage'] for x in g):<10.2f}"
              f"{mean(x['accuracy'] for x in g):<10.2f}{mean(x['readability'] for x in g):<12.2f}")

    print("\nSUMMARY COVERAGE by document (mean, 1-5)")
    cases = list(dict.fromkeys(r["case"] for r in rows))
    print(f"{'Method':<18}" + "".join(f"{c:<24}" for c in cases))
    for m in ("studymate", "lead_n_baseline", "t5_small"):
        vals = [mean(x["coverage"] for x in summ[m] if x["case"] == c) for c in cases]
        print(f"{m:<18}" + "".join(f"{v:<24.2f}" for v in vals))

    print("\nQUIZ QUESTIONS: share rated Y")
    print(f"{'Method':<18}{'n':<5}{'Accurate':<10}{'Relevant':<10}{'No clues':<10}{'All three':<10}")
    quiz = defaultdict(list)
    for r in rows:
        if r["type"] == "quiz":
            quiz[r["method"]].append(r)
    for m in ("studymate", "lead_n_baseline"):
        g = quiz[m]
        share = lambda f: sum(x[f] == "Y" for x in g) / len(g)
        all3 = sum(all(x[f] == "Y" for f in ("accurate", "relevant", "no_clues")) for x in g) / len(g)
        print(f"{m:<18}{len(g):<5}{share('accurate'):<10.2f}{share('relevant'):<10.2f}"
              f"{share('no_clues'):<10.2f}{all3:<10.2f}")

    print("\nQUIZ 'All three = Y' by document")
    for m in ("studymate", "lead_n_baseline"):
        parts = []
        for c in cases:
            g = [x for x in quiz[m] if x["case"] == c]
            ok = sum(all(x[f] == "Y" for f in ("accurate", "relevant", "no_clues")) for x in g)
            parts.append(f"{c}: {ok}/{len(g)}")
        print(f"  {m:<18}" + " | ".join(parts))

    if len(raters) > 1:
        print("\nDISAGREEMENTS (same output rated differently; IDs differ per rater, so items are matched by text)")
        groups = defaultdict(dict)
        for r in rows:
            groups[(r["case"], r["type"], r["method"], r["text"])][r["rater"]] = r
        n_shared = n_dis = 0
        for (case, typ, method, text), by_rater in groups.items():
            if len(by_rater) < 2:
                continue
            n_shared += 1
            fields = ("coverage", "accuracy", "readability") if typ == "summary" else ("accurate", "relevant", "no_clues")
            diffs = []
            for f in fields:
                vals = {rt: by_rater[rt][f] for rt in sorted(by_rater)}
                if len(set(vals.values())) > 1 and (typ == "quiz" or max(vals.values()) - min(vals.values()) >= 2):
                    diffs.append(f"{f} " + "/".join(f"{rt}={v}" for rt, v in vals.items()))
            if diffs:
                n_dis += 1
                print(f"  {case} | {typ} | {method} | {text[:60]}...")
                print(f"      {'; '.join(diffs)}")
        print(f"  {n_dis} of {n_shared} shared items disagree "
              f"(quiz: any Y/N difference; summaries: a 2+ point gap on a 1-5 score)")

        print("\nAGREEMENT on quiz Y/N ratings (share of identical judgments)")
        for f in ("accurate", "relevant", "no_clues"):
            pairs = [g for g in groups.values() if len(g) >= 2 and next(iter(g.values()))["type"] == "quiz"]
            same = sum(len({g[rt][f] for rt in g}) == 1 for g in pairs)
            print(f"  {f:<10} {same}/{len(pairs)} = {same / len(pairs):.2f}")
    else:
        print("\nOnly one rater: no inter-rater disagreement to report.")

if __name__ == "__main__":
    main()
