"""
StudyMate baseline artifact (Checkpoint 1).

Rule-based extractive summarizer + fill-in-the-blank quiz generator.
Uses only the Python standard library so it runs with no internet access
and no model downloads. This is the baseline the Checkpoint 2 pipeline
(pretrained T5 / Hugging Face summarization + question generation) is
meant to beat.

Usage:
    python3 studymate_baseline.py sample_notes.txt
"""

import re
import string
import sys
from collections import Counter

STOPWORDS = set("""
a an the and or but if while is are was were be been being have has had
do does did to of in on at for with by from as that this these those
it its it's he she they them his her their our your you i we not no
so than then there here when where why how what which who whom
can could will would shall should may might must about into over under
between among during before after above below up down out off again
further once more most other some such only own same too very just
also both each few more most other some such nor not only own same
into onto within without through per via versus vs etc
""".split())

_word_re = re.compile(r"[A-Za-z][A-Za-z\-']*")
_sentence_split_re = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def split_sentences(text):
    text = re.sub(r"\s+", " ", text.strip())
    sentences = _sentence_split_re.split(text)
    return [s.strip() for s in sentences if s.strip()]


def split_paragraphs_into_sentences(text):
    """Like split_sentences, but also returns which paragraph each sentence
    came from, so a summary can be built to cover every paragraph instead of
    clustering on whichever topic has the highest word frequency."""
    paragraphs = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    sentences = []
    paragraph_of = []
    for p_idx, paragraph in enumerate(paragraphs):
        for s in split_sentences(paragraph):
            sentences.append(s)
            paragraph_of.append(p_idx)
    return sentences, paragraph_of


def tokenize(sentence):
    return _word_re.findall(sentence)


def word_frequencies(sentences):
    freq = Counter()
    for sentence in sentences:
        for word in tokenize(sentence):
            lw = word.lower()
            if lw not in STOPWORDS and len(lw) > 2:
                freq[lw] += 1
    return freq


def score_sentences(sentences, freq):
    scores = []
    for idx, sentence in enumerate(sentences):
        words = [w.lower() for w in tokenize(sentence)]
        content_words = [w for w in words if w not in STOPWORDS and len(w) > 2]
        if not content_words:
            scores.append(0.0)
            continue
        raw = sum(freq[w] for w in content_words)
        scores.append(raw / len(content_words))
    return scores


def summarize(text, ratio=0.3, min_sentences=2):
    """Extractive summary that guarantees at least one sentence per
    paragraph before filling the rest of the budget by frequency score.

    Checkpoint 1 feedback: a pure top-N-by-frequency summary covered
    search/insertion but dropped deletion and balanced trees because those
    paragraphs used lower-frequency words. Reserving one slot per paragraph
    fixes that without discarding the frequency ranking.

    Checkpoint 2 feedback: when the ratio-based budget was smaller than the
    paragraph count, the one-slot-per-paragraph guarantee silently broke --
    the fix only had enough slots for some paragraphs' representative
    sentences, and which ones survived depended on Python's set-iteration
    order, not any real decision. Rather than let that happen, the budget is
    raised to the paragraph count whenever there are more paragraphs than
    the nominal ratio would keep, so every paragraph always gets a
    representative sentence; the realized compression ratio can therefore
    exceed the requested ratio for short, many-paragraph documents.
    """
    sentences, paragraph_of = split_paragraphs_into_sentences(text)
    if len(sentences) <= min_sentences:
        return sentences, sentences
    freq = word_frequencies(sentences)
    scores = score_sentences(sentences, freq)
    n_keep = max(min_sentences, round(len(sentences) * ratio))

    best_in_paragraph = {}
    for i, p in enumerate(paragraph_of):
        if p not in best_in_paragraph or scores[i] > scores[best_in_paragraph[p]]:
            best_in_paragraph[p] = i
    n_paragraphs = len(best_in_paragraph)
    n_keep = max(n_keep, n_paragraphs)

    keep_idx = set(best_in_paragraph.values())
    ranked_idx = sorted(range(len(sentences)), key=lambda i: scores[i], reverse=True)
    for i in ranked_idx:
        if len(keep_idx) >= n_keep:
            break
        keep_idx.add(i)

    summary = [sentences[i] for i in sorted(keep_idx)]
    return summary, sentences


def looks_like_key_term(word):
    return word[0].isupper() and word.lower() not in STOPWORDS and len(word) > 2


def pick_blank_term(sentence, freq):
    words = tokenize(sentence)
    candidates = [w for w in words if looks_like_key_term(w)]
    if not candidates:
        candidates = [w for w in words if w.lower() not in STOPWORDS and len(w) > 3]
    if not candidates:
        return None
    candidates.sort(key=lambda w: freq[w.lower()], reverse=True)
    return candidates[0]


def make_quiz(sentences, freq, n_questions=5):
    scored = sorted(
        range(len(sentences)),
        key=lambda i: score_sentences([sentences[i]], freq)[0],
        reverse=True,
    )
    quiz = []
    used_answers = set()
    for idx in scored:
        if len(quiz) >= n_questions:
            break
        sentence = sentences[idx]
        term = pick_blank_term(sentence, freq)
        if not term or term.lower() in used_answers:
            continue
        # count=0 blanks every occurrence of the term in this sentence.
        # Checkpoint 1 feedback: blanking only the first occurrence left the
        # answer ("search") visible later in the same question.
        blanked = re.sub(rf"\b{re.escape(term)}\b", "_____", sentence, count=0, flags=re.IGNORECASE)
        quiz.append({"question": blanked, "answer": term})
        used_answers.add(term.lower())
    return quiz


def run(path, summary_ratio=0.3, n_questions=5):
    text = read_text(path)
    summary_sentences, all_sentences = summarize(text, ratio=summary_ratio)
    freq = word_frequencies(all_sentences)
    quiz = make_quiz(all_sentences, freq, n_questions=n_questions)

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for s in summary_sentences:
        print(f"- {s}")

    print()
    print("=" * 60)
    print("QUIZ")
    print("=" * 60)
    for i, item in enumerate(quiz, start=1):
        print(f"{i}. {item['question']}")

    print()
    print("=" * 60)
    print("ANSWER KEY")
    print("=" * 60)
    for i, item in enumerate(quiz, start=1):
        print(f"{i}. {item['answer']}")

    print()
    print("=" * 60)
    print("STATS")
    print("=" * 60)
    print(f"Input sentences: {len(all_sentences)}")
    print(f"Summary sentences: {len(summary_sentences)}")
    compression = len(summary_sentences) / len(all_sentences) if all_sentences else 0
    print(f"Compression ratio: {compression:.2f}")
    print(f"Quiz questions generated: {len(quiz)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 studymate_baseline.py <notes.txt>")
        sys.exit(1)
    run(sys.argv[1])
