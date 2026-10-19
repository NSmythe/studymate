## Human Evaluation

**Setup.** Two human raters (R2 and R3) scored the outputs for three topics: binary search trees, hash tables and cellular respiration. Raters didn't know which method produced each item, and each rater saw the items in a different random order. They scored summaries from 1 to 5 on coverage, accuracy and readability. They rated quiz questions Y or N on three questions: is it accurate, is it relevant, and is it free of clues?

**Table 1. Summary ratings (mean, 1–5; n = 6 per method)**

| Method | Coverage | Accuracy | Readability |
|---|:-:|:-:|:-:|
| **StudyMate** | **4.17** | 5.00 | 4.33 |
| Lead-N baseline | 2.00 | 5.00 | **5.00** |
| T5-small | 2.33 | 2.67 | 2.00 |

**Table 2. Quiz question ratings (share rated Y; n = 30 per method)**

| Method | Accurate | Relevant | No clues | All three |
|---|:-:|:-:|:-:|:-:|
| **StudyMate** | 1.00 | **0.60** | **0.73** | **0.60** |
| Lead-N baseline | 1.00 | 0.27 | 0.70 | 0.23 |

**Findings.**

- StudyMate's summaries had the highest coverage (4.17, compared with 2.00 for Lead-N and 2.33 for T5-small). They kept full accuracy (5.00) and lost a little readability compared with Lead-N (4.33 vs. 5.00).
- T5-small scored lowest on accuracy (2.67) and readability (2.00). Rater comments point to factual errors and broken text.
- Every quiz question from both methods was rated accurate. StudyMate's questions were rated relevant much more often (0.60 vs. 0.27) and met all three criteria more often (0.60 vs. 0.23). This is mainly because the baseline often blanked out part of the topic name or a general word.

**Rater agreement.** The two raters gave the same quiz rating on 30/30 items for *accurate*, 30/30 for *relevant* and 29/30 for *no clues*. Only 1 of the 39 items both raters scored had a disagreement: a quiz Y/N difference, or a gap of 2+ points on a summary score.

**AI judge (reported separately).** An AI model also rated every item blind. Its scores are **not** included in Tables 1 or 2.

| What was compared | Agreement with the human raters |
|---|---|
| Quiz: accurate / relevant / no clues | 30/30 · 28/30 · 18/30 |
| Summaries: average score difference (coverage / accuracy / readability) | 0.28 · 0.11 · 0.22 points |

The AI judge agreed with the human raters on which methods did best and on accuracy and relevance. It was much stricter on *no clues*, especially for baseline questions (0.13 Y vs. 0.70 for humans). It also scored StudyMate's summary coverage lower (3.33 vs. 4.17).

**Limitations.** There were only two human raters and three topics, so each summary average rests on six ratings. With so few raters, the high agreement may not hold up with a larger group. The AI judge is a single model and may be biased in consistent ways.
