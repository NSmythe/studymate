"""
Checkpoint 2 evaluation harness.

Runs the StudyMate method (frequency-scored extractive summary with
per-paragraph coverage, from studymate_baseline.py) against a Lead-N
baseline (simple_baseline.py) on three documents, two of which are unseen
notes on different topics from the Checkpoint 1 sample, per reviewer
feedback asking for tests "on several unseen notes from different topics."

For each (method, document) pair this measures:
  - compression ratio (summary sentences / input sentences)
  - key-concept coverage: fraction of a manually curated list of the
    document's key terms that appear (case-insensitive substring) anywhere
    in the generated summary. This is an automatic proxy for "does the
    summary cover the material," not a judgment of writing quality.
  - quiz questions generated
  - leaked answers: how many quiz questions still show their own answer
    term elsewhere in the blanked question text (the Checkpoint 1 bug)

Human review of question accuracy/relevance (the measure defined in the
Checkpoint 1 report) is NOT run here — mark as not yet completed.
"""

import re

from studymate_baseline import read_text, summarize, word_frequencies, make_quiz, split_sentences
from simple_baseline import lead_quiz
from t5_summarizer import t5_summarize, token_length

CASES = [
    {
        "name": "binary_search_trees",
        "path": "sample_notes.txt",
        "key_concepts": [
            "binary search tree", "search", "insertion", "deletion",
            "balanced", "AVL", "red-black", "logarithmic",
        ],
    },
    {
        "name": "hash_tables",
        "path": "sample_notes_hashing.txt",
        "key_concepts": [
            "hash function", "collision", "chaining", "open addressing",
            "load factor", "O(1)", "O(n)", "rehash",
        ],
    },
    {
        "name": "cellular_respiration",
        "path": "sample_notes_cellular_respiration.txt",
        "key_concepts": [
            "glycolysis", "citric acid cycle", "electron transport chain",
            "ATP", "mitochondria", "oxygen", "NADH",
        ],
    },
]


def word_ratio(summary_sentences, text):
    """Compression in words, so extractive and abstractive outputs compare fairly."""
    return len(" ".join(summary_sentences).split()) / len(text.split())


def concept_coverage(summary_sentences, key_concepts):
    text = " ".join(summary_sentences).lower()
    hit = [c for c in key_concepts if c.lower() in text]
    return len(hit) / len(key_concepts), hit


def count_leaks(quiz):
    leaks = 0
    for item in quiz:
        remainder = re.sub(r"_____", "", item["question"], flags=re.IGNORECASE)
        if re.search(rf"\b{re.escape(item['answer'])}\b", remainder, flags=re.IGNORECASE):
            leaks += 1
    return leaks


def run_case(case):
    text = read_text(case["path"])
    results = {}

    sm_summary, sm_sentences = summarize(text, ratio=0.3)
    sm_freq = word_frequencies(sm_sentences)
    sm_quiz = make_quiz(sm_sentences, sm_freq, n_questions=5)
    sm_coverage, sm_hits = concept_coverage(sm_summary, case["key_concepts"])
    results["studymate"] = {
        "n_input": len(sm_sentences),
        "n_summary": len(sm_summary),
        "compression": word_ratio(sm_summary, text),
        "coverage": sm_coverage,
        "covered_concepts": sm_hits,
        "n_quiz": len(sm_quiz),
        "leaks": count_leaks(sm_quiz),
    }

    # Equal budget: Lead-N keeps exactly as many sentences as StudyMate, whose
    # paragraph guarantee can raise its budget above round(0.3 * n).
    lead_sentences = split_sentences(text)
    lead_summary = lead_sentences[: len(sm_summary)]
    lq = lead_quiz(lead_sentences, n_questions=5)
    lead_coverage, lead_hits = concept_coverage(lead_summary, case["key_concepts"])
    results["lead_n_baseline"] = {
        "n_input": len(lead_sentences),
        "n_summary": len(lead_summary),
        "compression": word_ratio(lead_summary, text),
        "coverage": lead_coverage,
        "covered_concepts": lead_hits,
        "n_quiz": len(lq),
        "leaks": count_leaks(lq),
    }

    # Pretrained abstractive summarizer, capped at StudyMate's token length.
    # Summary only: t5-small has no quiz generator, so quiz/leaks are n/a.
    budget = token_length(" ".join(sm_summary))
    t5_summary, truncated = t5_summarize(text, max_new_tokens=budget)
    t5_coverage, t5_hits = concept_coverage(t5_summary, case["key_concepts"])
    results["t5_small"] = {
        "n_input": len(sm_sentences),
        "n_summary": len(t5_summary),
        "compression": word_ratio(t5_summary, text),
        "coverage": t5_coverage,
        "covered_concepts": t5_hits,
        "n_quiz": None,
        "leaks": None,
        "truncated": truncated,
        "summary_text": " ".join(t5_summary),
    }
    return results


def main():
    all_results = {}
    print(f"{'Case':<24}{'Method':<18}{'Words%':<13}{'Coverage':<10}{'Quiz':<6}{'Leaks':<6}")
    print("-" * 77)
    for case in CASES:
        res = run_case(case)
        all_results[case["name"]] = res
        for method, r in res.items():
            quiz = "n/a" if r["n_quiz"] is None else r["n_quiz"]
            leaks = "n/a" if r["leaks"] is None else r["leaks"]
            print(
                f"{case['name']:<24}{method:<18}"
                f"{r['compression']:<13.2f}{r['coverage']:<10.2f}{quiz:<6}{leaks:<6}"
            )
    print()
    print("Concept coverage detail (which key concepts each method's summary mentions):")
    for case in CASES:
        res = all_results[case["name"]]
        print(f"\n{case['name']} (key concepts: {case['key_concepts']})")
        for method, r in res.items():
            print(f"  {method}: {r['covered_concepts']}")
    print("\nt5_small raw summaries (for inspection / human review):")
    for case in CASES:
        r = all_results[case["name"]]["t5_small"]
        print(f"\n{case['name']} (input truncated to 512 tokens: {r['truncated']})")
        print(f"  {r['summary_text']}")
    return all_results


if __name__ == "__main__":
    main()
