"""
Builds blind human-review sheets for the final evaluation.

Each rater gets one Word document with the source notes, then the outputs of
all methods with the method names hidden and the order shuffled (a different
shuffle per rater, fixed by a seed so the sheets can be rebuilt exactly).
The mapping from item IDs to methods goes in a separate key file that raters
never see.

Usage:
    python3 make_rating_sheets.py
Output (in rating_sheets/):
    R1.docx, R2.docx, R3.docx   one sheet per rater
    key_PRIVATE.csv             item ID -> method (do not share with raters)
    ratings.csv                 blank table for typing in the raters' scores
"""

import csv
import html
import os
import random
import subprocess

from evaluate import CASES
from simple_baseline import lead_quiz
from studymate_baseline import make_quiz, read_text, split_sentences, summarize, word_frequencies
from t5_summarizer import t5_summarize, token_length

RATERS = ["R1", "R2", "R3"]
OUT_DIR = "rating_sheets"

INSTRUCTIONS = """
<h1>StudyMate Review Sheet: Rater {rater}</h1>
<p>Thank you for helping. Please do not write your name anywhere on this sheet.</p>
<p><b>How to rate:</b> For each topic, read the <b>source notes</b> first. Then rate
the summaries and quiz questions that follow. Judge everything only against
the source notes, so you do not need to already know the subject. The items
come from different methods in random order. Rate each one on its own.</p>
<p><b>Summaries</b> (write a number in each box):</p>
<ul>
<li><b>Coverage</b>: 1 = misses most main ideas, 3 = covers about half, 5 = covers all the main ideas.</li>
<li><b>Accuracy</b>: 1 = several false or confusing statements, 3 = one clear error, 5 = everything matches the notes.</li>
<li><b>Readability</b>: 1 = hard to read or broken text, 5 = clear and easy to read.</li>
</ul>
<p><b>Quiz questions</b> (write Y or N in each box):</p>
<ul>
<li><b>Accurate</b>: with the answer filled in, the statement is true according to the notes.</li>
<li><b>Relevant</b>: it tests an important idea, not a minor detail or a random word.</li>
<li><b>No clues</b>: a student could not answer it just from hints in the question itself.</li>
</ul>
<p>Use the <b>Comments</b> box to note anything wrong or confusing. Comments are optional but very helpful.</p>
"""


def build_items():
    """Returns {case_name: {"source": text, "summaries": [...], "quiz": [...]}}."""
    data = {}
    for case in CASES:
        text = read_text(case["path"])
        sm_summary, sm_sentences = summarize(text, ratio=0.3)
        sm_quiz = make_quiz(sm_sentences, word_frequencies(sm_sentences), n_questions=5)
        lead_sentences = split_sentences(text)
        lead_summary = lead_sentences[: len(sm_summary)]
        lq = lead_quiz(lead_sentences, n_questions=5)
        t5_summary, _ = t5_summarize(text, max_new_tokens=token_length(" ".join(sm_summary)))

        summaries = [
            ("studymate", " ".join(sm_summary)),
            ("lead_n_baseline", " ".join(lead_summary)),
            ("t5_small", " ".join(t5_summary)),
        ]
        quiz = [("studymate", q) for q in sm_quiz] + [("lead_n_baseline", q) for q in lq]
        data[case["name"]] = {"source": text, "summaries": summaries, "quiz": quiz}
    return data


def table(header, rows):
    head = "".join(f"<th>{h}</th>" for h in header)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<table border="1" cellpadding="4" cellspacing="0"><tr>{head}</tr>{body}</table>'


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    data = build_items()
    key_rows, rating_rows = [], []

    for r_idx, rater in enumerate(RATERS):
        rng = random.Random(1000 + r_idx)
        parts = [INSTRUCTIONS.format(rater=rater)]
        for t_idx, (case_name, d) in enumerate(data.items(), start=1):
            title = case_name.replace("_", " ").title()
            paras = "".join(f"<p>{html.escape(p.strip())}</p>" for p in d["source"].split("\n\n") if p.strip())
            parts.append(f"<h2>Topic {t_idx}: {title}</h2><h3>Source notes</h3>{paras}")

            summaries = d["summaries"][:]
            rng.shuffle(summaries)
            parts.append("<h3>Summaries</h3>")
            for s_idx, (method, summary) in enumerate(summaries):
                item_id = f"T{t_idx}-S{chr(65 + s_idx)}"
                key_rows.append([rater, item_id, case_name, "summary", method])
                rating_rows.append([rater, item_id, "", "", "", "", "", "", ""])
                parts.append(f"<p><b>Summary {item_id}</b></p><p>{html.escape(summary)}</p>")
                parts.append(table(["Coverage (1-5)", "Accuracy (1-5)", "Readability (1-5)", "Comments"], [["&nbsp;"] * 4]))

            quiz = d["quiz"][:]
            rng.shuffle(quiz)
            parts.append("<h3>Quiz questions</h3>")
            rows = []
            for q_idx, (method, q) in enumerate(quiz, start=1):
                item_id = f"T{t_idx}-Q{q_idx}"
                key_rows.append([rater, item_id, case_name, "quiz", method])
                rating_rows.append([rater, item_id, "", "", "", "", "", "", ""])
                rows.append([item_id, html.escape(q["question"]), html.escape(q["answer"]), "", "", "", ""])
            parts.append(table(["ID", "Question", "Answer", "Accurate (Y/N)", "Relevant (Y/N)", "No clues (Y/N)", "Comments"], rows))

        html_path = os.path.join(OUT_DIR, f"{rater}.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("<html><body>" + "".join(parts) + "</body></html>")
        subprocess.run(["textutil", "-convert", "docx", html_path], check=True)
        os.remove(html_path)

    with open(os.path.join(OUT_DIR, "key_PRIVATE.csv"), "w", newline="") as f:
        csv.writer(f).writerows([["rater", "item_id", "case", "type", "method"]] + key_rows)
    with open(os.path.join(OUT_DIR, "ratings.csv"), "w", newline="") as f:
        csv.writer(f).writerows(
            [["rater", "item_id", "coverage", "accuracy", "readability", "accurate", "relevant", "no_clues", "comments"]]
            + rating_rows
        )
    print(f"Wrote {len(RATERS)} sheets, key_PRIVATE.csv, and ratings.csv to {OUT_DIR}/")


if __name__ == "__main__":
    main()
