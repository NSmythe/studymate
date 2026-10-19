"""
Lead-N baseline for comparison (Checkpoint 2).

This is the simple method the StudyMate pipeline (studymate_baseline.py,
frequency-scored extractive summary + paragraph coverage) is compared
against: take the first N sentences of the document as the summary, and
build quiz questions from those same leading sentences in document order.
It has no notion of word frequency or importance, so it is expected to lose
on topic coverage once content it doesn't mention appears later in the
notes.
"""

import re
from studymate_baseline import split_sentences, tokenize, STOPWORDS


def lead_summarize(text, ratio=0.3, min_sentences=2):
    sentences = split_sentences(text)
    if len(sentences) <= min_sentences:
        return sentences, sentences
    n_keep = max(min_sentences, round(len(sentences) * ratio))
    return sentences[:n_keep], sentences


def lead_quiz(sentences, n_questions=5):
    quiz = []
    used_answers = set()
    for sentence in sentences:
        if len(quiz) >= n_questions:
            break
        words = tokenize(sentence)
        candidates = [w for w in words if w.lower() not in STOPWORDS and len(w) > 3]
        term = None
        for w in candidates:
            if w.lower() not in used_answers:
                term = w
                break
        if not term:
            continue
        blanked = re.sub(rf"\b{re.escape(term)}\b", "_____", sentence, count=0, flags=re.IGNORECASE)
        quiz.append({"question": blanked, "answer": term})
        used_answers.add(term.lower())
    return quiz
