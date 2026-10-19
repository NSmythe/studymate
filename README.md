# StudyMate: Note Summarizer & Quiz Generator

StudyMate turns plain-text course notes into a short summary and a set of
fill-in-the-blank quiz questions with an answer key. This repository contains
the code, data, and evaluation scripts used to produce the results in the
COMP 365 individual project paper.

## Methods compared

| Method | File | Type | Produces |
|---|---|---|---|
| **StudyMate** | `studymate_baseline.py` | Rule-based extractive. Scores sentences by word frequency and keeps at least one sentence from every paragraph. | Summary + quiz |
| **Lead-N baseline** | `simple_baseline.py` | Takes the first N sentences. Same summary length as StudyMate. | Summary + quiz |
| **T5-small** | `t5_summarizer.py` | Pretrained abstractive model ([`t5-small`](https://huggingface.co/t5-small), Raffel et al., 2020), used as-is with **no fine-tuning**. Output capped at StudyMate's token length. | Summary only |

## Repository contents

| File | Purpose |
|---|---|
| `sample_notes.txt` | Binary search trees notes (18 sentences, 5 paragraphs) |
| `sample_notes_hashing.txt` | Hash tables notes (16 sentences, 5 paragraphs) |
| `sample_notes_cellular_respiration.txt` | Cellular respiration notes (15 sentences, 5 paragraphs) |
| `evaluate.py` | Automatic evaluation: summary length and key-concept coverage for all 3 methods, plus quiz answer leaks |
| `results.txt` | Saved output of `evaluate.py` |
| `make_rating_sheets.py` | Builds the human review sheets (method names hidden, order shuffled) |
| `score_ratings.py` | Scores filled-in review sheets and prints per-method results |
| `human_review_results.txt` | Saved output of `score_ratings.py` (human raters only) |
| `compare_ai_judge.py` | Compares the separate AI judge ratings with the human ratings |
| `rating_sheets/R1_ai_reference.docx` | AI judge ratings on the R1 sheet. Reported separately; **not** included in human results |
| `rating_sheets/R2_filled.docx` | Completed review sheet: independent CS student reviewer (R2) |
| `rating_sheets/R3_filled.docx` | Completed review sheet: undergraduate Business Management reviewer (R3) |
| `rating_sheets/ai_judge_comparison.txt` | Saved output of `compare_ai_judge.py` |
| `rating_sheets/key_PRIVATE.csv` | Maps each review item to the method that produced it |
| `rating_sheets/ratings.csv` | All human ratings (R2, R3) matched to methods |

All three notes files are synthetic study notes written for this project. They
contain no personal or third-party data.

## Requirements

- macOS (tested on macOS 26.6.2, Apple M3, 24 GB RAM). Runs on CPU; no GPU needed.
- Python 3.14.6 (any recent Python 3 should work)
- Packages and versions: see `requirements.txt`
- About 250 MB of disk space for the T5-small model
- `make_rating_sheets.py` and `score_ratings.py` use macOS's built-in `textutil`
  to read and write Word files, so those two scripts need macOS.

StudyMate and Lead-N use only the Python standard library. Only the T5-small
comparison needs the packages in `requirements.txt`.

## Setup

1. Clone the repository and enter the folder:
   ```bash
   git clone https://github.com/NSmythe/studymate.git
   cd studymate
   ```
2. Install the dependencies:
   ```bash
   python3 -m pip install -r requirements.txt
   ```
3. Download the T5-small model once (needs internet, about 240 MB):
   ```bash
   python3 -c "from transformers import AutoModelForSeq2SeqLM; AutoModelForSeq2SeqLM.from_pretrained('t5-small')"
   ```
   After this, `t5_summarizer.py` runs offline from the local cache.

## Running

**Summarize one document and generate a quiz** (StudyMate only, no packages needed):
```bash
python3 studymate_baseline.py sample_notes.txt
```

**Reproduce the automatic evaluation** (about 15 seconds):
```bash
python3 evaluate.py
```
The output should match `results.txt`. A warning that the binary search trees
notes are longer than 512 tokens is expected: T5-small reads at most 512
tokens, so the end of that document is cut off.

**Reproduce the human review results:**
```bash
python3 score_ratings.py
```
The output should match `human_review_results.txt`.

**Reproduce the AI judge comparison** (run after `score_ratings.py`):
```bash
python3 compare_ai_judge.py
```
The output should match `rating_sheets/ai_judge_comparison.txt`.

**Rebuild the blank review sheets** (optional):
```bash
python3 make_rating_sheets.py
```
This regenerates `R1.docx`, `R2.docx`, `R3.docx`, and the key. The shuffle uses
fixed seeds, so the sheets come out the same every time.

## Settings used for the reported results

| Setting | Value |
|---|---|
| Summary ratio (StudyMate) | 0.3 of sentences, raised to the paragraph count if needed |
| Lead-N summary length | Same number of sentences as StudyMate |
| T5-small output length | `max_new_tokens` = StudyMate summary's token length; `min_new_tokens` = 80% of that |
| T5-small decoding | Beam search, `num_beams=4`, `no_repeat_ngram_size=3`, no sampling |
| T5-small input limit | 512 tokens (longer input is truncated) |
| T5-small checkpoint | Hugging Face revision `df1b051c49625cf57a3d0d8d3863ed4d13564fe4` |
| Quiz questions per document | 5 |

## Human review

Each review sheet holds 39 items: 9 summaries (3 documents x 3 methods) and
30 quiz questions (15 StudyMate, 15 Lead-N). Summaries are rated 1-5 on
coverage, accuracy, and readability. Quiz questions are rated Y/N on whether
they are accurate, relevant, and answerable without clues from the question
itself. Method names are hidden and items are shuffled differently for each
rater. Two human raters completed the review independently with the same rubric:

- **R2**: an undergraduate CS student, who did not know which method produced each item
- **R3**: an undergraduate Business Management major, who did not know which method produced each item

An AI model also completed the R1 sheet blind, as a separate **AI judge**. Its
ratings are saved in `rating_sheets/R1_ai_reference.docx`. The file name does not
match `R*_filled.docx`, so `score_ratings.py` leaves it out of the human results.
`compare_ai_judge.py` reports it separately.

No names or personal information were collected. `score_ratings.py` reports
per-method results for the human raters combined, plus every item where they
disagree and the agreement rate on each quiz criterion.

## AI assistance

- **Gemini** helped with code fixes and the first version of the evaluation harness (Checkpoint 2) and helped produce separate judge ratings for R1.

The evaluation design, the human ratings (R2, R3), and the conclusions are the author's own.
