"""
Pretrained abstractive baseline: t5-small (Raffel et al., 2020), used as-is
with no fine-tuning, via Hugging Face Transformers.

The output length is capped at the token length of the StudyMate summary for
the same document, so all methods are compared at roughly the same budget.
Inputs longer than 512 tokens are truncated, which is a limit of t5-small.

Setup (one time, needs internet):
    python3 -c "from transformers import AutoModelForSeq2SeqLM; AutoModelForSeq2SeqLM.from_pretrained('t5-small')"
"""

import os

os.environ.setdefault("HF_HUB_OFFLINE", "1")  # use the local cache only

from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, set_seed

from studymate_baseline import split_sentences

MODEL_NAME = "t5-small"
MAX_INPUT_TOKENS = 512
GEN_SETTINGS = {"num_beams": 4, "no_repeat_ngram_size": 3, "do_sample": False}

_tok = None
_model = None


def _load():
    global _tok, _model
    if _model is None:
        set_seed(0)
        _tok = AutoTokenizer.from_pretrained(MODEL_NAME)
        _model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    return _tok, _model


def token_length(text):
    tok, _ = _load()
    return len(tok(text).input_ids)


def t5_summarize(text, max_new_tokens):
    """Returns (summary_sentences, was_truncated)."""
    tok, model = _load()
    enc = tok("summarize: " + text, return_tensors="pt")
    truncated = enc.input_ids.shape[1] > MAX_INPUT_TOKENS
    ids = enc.input_ids[:, :MAX_INPUT_TOKENS]
    out = model.generate(
        ids,
        max_new_tokens=max_new_tokens,
        min_new_tokens=int(max_new_tokens * 0.8),
        **GEN_SETTINGS,
    )
    summary = tok.decode(out[0], skip_special_tokens=True)
    return split_sentences(summary), truncated
