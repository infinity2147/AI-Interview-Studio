# analysis_pipeline.py
from typing import Dict, Any
import re

FILLERS = ["um", "uh", "like", "you know", "so", "actually"]

def compute_basic_features(transcript: str) -> Dict[str, Any]:
    text = transcript.lower()
    words = re.findall(r"\w+", text)
    word_count = len(words)
    filler_count = sum(text.count(f) for f in FILLERS)
    avg_word_len = (sum(len(w) for w in words) / word_count) if word_count else 0
    return {
        "word_count": word_count,
        "filler_count": filler_count,
        "avg_word_len": avg_word_len
    }

def evaluate_answer(transcript: str, competencies: list) -> Dict[str, Any]:
    """
    Return per-competency scores (0-10), prosody-like signals and a short comment.
    Very simple rules-based evaluator designed for demo/training purposes.
    """
    feats = compute_basic_features(transcript)
    base = max(0, min(10, 6 + (feats["word_count"] - 20) / 20))  # modest scaling
    # penalty for fillers
    base = base - min(2.0, 0.4 * feats["filler_count"])
    results = {}
    comments = []
    # sample domain keywords for technical questions
    tech_keywords = ["profiler", "optimiz", "cache", "sql", "bottleneck", "thread", "async", "scal"]
    for comp in competencies:
        score = base
        text_lower = transcript.lower()
        if comp in ("technical_knowledge", "problem_solving", "analytical_thinking"):
            if any(k in text_lower for k in tech_keywords):
                score += 1.2
            comments.append("Shows technical keywords." if any(k in text_lower for k in tech_keywords) else "")
        if comp == "communication":
            # penalize many fillers
            score -= 0.2 * feats["filler_count"]
        results[comp] = round(max(0.0, min(10.0, score)),2)
    # summary comment
    summary = "Good structure." if feats["word_count"] > 20 else "Answer is short; expand with examples."
    return {
        "scores": results,
        "features": feats,
        "comment": summary
    }
