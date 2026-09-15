"""
Phase 9 RAG answer evaluator.

Public API (both old names and enhanced names are exported):
  check_answer_points(answer_text, expected) -> dict
  check_forbidden_claims(answer_text, forbidden) -> dict          # alias
  check_forbidden_claims_enhanced(answer_text, forbidden) -> dict # canonical
  check_abstention_behavior(answer_text, case) -> dict            # alias
  check_abstention_behavior_enhanced(answer_text, case) -> dict   # canonical
  check_source_alignment(answer_text, retrieved_titles) -> dict
  evaluate_case(case, answer_text, retrieved_titles) -> dict
"""
from __future__ import annotations

import re
from typing import Any

from apps.knowledge.evaluation.rag_evaluation_dataset import RAGEvaluationCase


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _normalize_text(text: str) -> str:
    """Remove punctuation, lower-case, and collapse whitespace."""
    normalized = re.sub(r'[,.;:!?"\-\'`]', ' ', text)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized.lower()


def _sentence_split(text: str) -> list[str]:
    """Split text into rough sentences."""
    return [s.strip() for s in re.split(r'[.!?;]\s+', text) if s.strip()]


def _claim_keywords(claim_text: str, min_len: int = 3) -> list[str]:
    """Return significant lower-cased words from a claim."""
    _STOPWORDS = {
        'a', 'an', 'the', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'could', 'should', 'may', 'might', 'shall', 'can',
        'to', 'of', 'in', 'on', 'at', 'by', 'for', 'with', 'about',
        'that', 'this', 'it', 'its',
    }
    return [
        w.lower() for w in claim_text.split()
        if len(w) >= min_len and w.lower() not in _STOPWORDS
    ]


# Contrastive connectors: patterns found in same sentence as claim keywords
# that indicate the concepts are being separated, not asserted together.
_CONTRASTIVE_CONNECTOR_RE = re.compile(
    r'\b('
    r'separate(?:s|d)?s?\s+(?:from|and)'
    r'|distinct\s+from'
    r'|not\s+the\s+same\s+as'
    r'|differ(?:s|ent)?\s+from'
    r'|instead\s+of'
    r'|rather\s+than'
    r'|as\s+opposed\s+to'
    r'|while\b'
    r'|\bwhereas\b'
    r'|\bbut\b'
    r'|\bhowever\b'
    r'|\beven\s+though\b'
    r')\b',
    re.IGNORECASE,
)

# "does not determine/decide/control/..." patterns
_NOT_VERB_RE = re.compile(
    r'\b(?:does\s+not|doesn\'t|is\s+not|are\s+not|was\s+not|never|not)\s+'
    r'(?:decide|determine|control|grant|assign|set|give|define|handle|manage|perform|execute)s?\b',
    re.IGNORECASE,
)

# "X is separate/distinct from Y"
_SEPARATION_RE = re.compile(
    r'\b(?:is|are|remains?)\s+(?:separate|distinct|different|independent)\b',
    re.IGNORECASE,
)

# Explicit partitioning: "handles X; handles Y" or "verifies X, while Y controls B"
# Also catches semicolon-based parallel constructions across clauses.
_PARTITION_RE = re.compile(
    r'\b(?:handles?|manages?|verifies?|checks?|evaluates?|controls?|performs?|is\s+responsible\s+for)'
    r'(?:\s+\w+){1,5}\s*[,;]\s*'
    r'(?:while\s+)?(?:and\s+)?(?:\w+(?:\s+\w+){0,3}\s+)?'
    r'(?:handles?|manages?|verifies?|checks?|evaluates?|controls?|performs?|is\s+responsible\s+for)\b',
    re.IGNORECASE,
)

# Semicolon-separated parallel verb pattern across the whole answer
# "A handles X; B handles Y" — two clauses with same verb class, different subjects
_SEMICOLON_PARALLEL_RE = re.compile(
    r'[^;.!?]+\b(?:handles?|manages?|verifies?|checks?|evaluates?|controls?|performs?)\b[^;.!?]*'
    r'[;]'
    r'[^;.!?]+\b(?:handles?|manages?|verifies?|checks?|evaluates?|controls?|performs?)\b',
    re.IGNORECASE,
)

# "not for / not to" purpose negation
_NOT_FOR_RE = re.compile(r'\bnot\s+(?:for|to)\b', re.IGNORECASE)


def _contrastive_context(answer_text: str, kws: list[str]) -> bool:
    """
    Return True when sentences containing claim keywords also express
    contrastive/separating language (i.e., the concepts are kept apart,
    not asserted together).

    Checks both sentence-level patterns and whole-answer parallel constructions
    (e.g., semicolon-separated clauses using the same verb class with different
    subjects: "Authentication handles identity; authorization handles roles").
    """
    sentences = _sentence_split(answer_text)
    lower_answer = answer_text.lower()

    # Whole-answer check: semicolon-separated parallel verb construction
    # This catches "X handles A; Y handles B" even when split into two sentences.
    if _SEMICOLON_PARALLEL_RE.search(answer_text):
        # Only relevant if at least one claim keyword appears in the answer
        if any(kw in lower_answer for kw in kws):
            return True

    for kw in kws:
        if kw not in lower_answer:
            continue
        for sent in sentences:
            if kw not in sent.lower():
                continue
            # Does this sentence express contrast/separation?
            if (
                _CONTRASTIVE_CONNECTOR_RE.search(sent)
                or _NOT_VERB_RE.search(sent)
                or _SEPARATION_RE.search(sent)
                or _PARTITION_RE.search(sent)
                or _NOT_FOR_RE.search(sent)
            ):
                return True
    return False


def _direct_negation_of_claim(
    normalized_answer: str,
    normalized_claim: str,
    kws: list[str],
) -> bool:
    """
    Return True when the answer contains an explicit local negation targeting
    the claim or its key concepts.
    """
    if f'not {normalized_claim}' in normalized_answer:
        return True
    for kw in kws:
        patterns = [
            rf'\bnot\s+{re.escape(kw)}\b',
            rf'\bdoes\s+not\s+{re.escape(kw)}\b',
            rf'\bwas\s+not\s+{re.escape(kw)}\b',
            rf'\bare\s+not\s+{re.escape(kw)}\b',
            rf'\bis\s+not\s+{re.escape(kw)}\b',
            rf'\bnever\s+{re.escape(kw)}\b',
        ]
        for p in patterns:
            if re.search(p, normalized_answer):
                return True
    return False


def _global_negation_present(normalized_answer: str) -> bool:
    """Broad document-level negation / inability / abstention markers."""
    patterns = [
        r'\bcannot\b', r'\bcan\s+not\b',
        r'\bdoes\s+not\b', r"\bdoesn't\b",
        r'\bi\s+don\'t\s+know\b', r'\bi\s+do\s+not\s+know\b',
        r'\bcannot\s+provide\b', r'\bcannot\s+tell\b',
        r'\bcannot\s+determine\b', r'\bcannot\s+answer\b',
        r'\binsufficient.*information\b',
        r'\bno.*evidence\b',
        r'\bis\s+not\s+true\b', r'\bis\s+false\b',
        r'\bdoes\s+not\s+exist\b', r'\bthere\s+is\s+no\b',
    ]
    for p in patterns:
        if re.search(p, normalized_answer):
            return True
    return False


# ---------------------------------------------------------------------------
# Core deterministic checks
# ---------------------------------------------------------------------------


def check_answer_points(answer_text: str, expected: tuple[str, ...]) -> dict:
    """Simple keyword/presence heuristic (not semantic judge)."""
    found = []
    missing = []
    lower_answer = answer_text.lower()
    for point in expected:
        keywords = [w.lower() for w in point.split() if len(w) > 3]
        hits = sum(1 for k in keywords if k in lower_answer)
        matched = hits >= max(1, len(keywords) // 2)
        if matched:
            found.append(point)
        else:
            missing.append(point)
    return {
        "found_points": found,
        "missing_points": missing,
        "score": len(found) / len(expected) if expected else 1.0,
    }


def check_forbidden_claims_enhanced(
    answer_text: str,
    forbidden: tuple[str, ...],
) -> dict:
    """
    Per-claim forbidden-claim detection with negation and contrastive-context
    awareness.

    A claim is a VIOLATION only when:
      - The claim phrase appears literally in the answer AND
        the answer does NOT negate or contrastively separate it, OR
      - The key concept words co-occur in the answer in an assertive way
        (not in a negated or contrastive construction).

    NOT a violation when the answer:
      - Contains an explicit local negation ("X does not decide Y")
      - Contains contrastive connectors in the same sentence ("while X handles
        identity, Y evaluates roles")
      - Uses separating constructions ("X is separate from Y")
    """
    normalized_answer = _normalize_text(answer_text)

    violations = []

    for claim in forbidden:
        if not claim:
            continue

        normalized_claim = _normalize_text(claim)
        kws = _claim_keywords(claim, min_len=3)

        if not kws:
            continue

        # ---- Step 1: literal phrase match ----
        literal_match = normalized_claim in normalized_answer

        if literal_match:
            negated = _direct_negation_of_claim(normalized_answer, normalized_claim, kws)
            contrastive = _contrastive_context(answer_text, kws)
            global_neg = _global_negation_present(normalized_answer)
            if negated or contrastive or global_neg:
                continue  # negated literal -- not a violation
            violations.append(claim)
            continue

        # ---- Step 2: keyword co-occurrence ----
        answer_words = set(normalized_answer.split())
        matching_kws = [kw for kw in kws if kw in answer_words]

        # Need at least half (min 2) of claim keywords
        required = max(2, len(kws) // 2)
        if len(matching_kws) < required:
            continue

        negated = _direct_negation_of_claim(normalized_answer, normalized_claim, kws)
        contrastive = _contrastive_context(answer_text, kws)
        global_neg = _global_negation_present(normalized_answer)

        if negated or contrastive or global_neg:
            continue  # concepts present but negated/separated -- not a violation

        violations.append(claim)

    return {
        "violations": violations,
        "passed": len(violations) == 0,
    }


# Backward-compat alias (Phase 7/8 tests import this name)
check_forbidden_claims = check_forbidden_claims_enhanced


def check_abstention_behavior_enhanced(
    answer_text: str,
    case: RAGEvaluationCase,
) -> dict:
    """
    Enhanced abstention detection.

    Detects when answers properly abstain from answering due to insufficient
    information, while distinguishing from actual forbidden claims that happen
    to be mentioned in unanswerable contexts.
    """
    if not case.unanswerable:
        return {"expected_abstain": False, "detected_abstain": False}

    abstain_indicators = (
        "insufficient", "not available", "does not contain",
        "no evidence", "i don't know", "i do not know",
        "cannot determine", "not enough information",
        "cannot answer", "cannot provide", "cannot tell",
        "not present", "not exist", "not found",
        "no information", "not mentioned", "not specified",
        "do not know", "don't know", "i'm not able",
        "not able to answer", "unable to answer",
        "the context does not contain", "there is no information",
        "there are no details", "lacks information", "no details available",
        "information not provided", "data not available", "no data",
        "not found in context", "not present in the context",
    )

    negation_phrases = (
        "cannot answer", "cannot provide", "cannot tell", "cannot determine",
        "cannot say", "cannot give", "cannot mention",
        "do not know", "don't know", "i do not know", "i'm not aware",
        "not able to answer", "unable to answer",
        "not able to provide", "unable to provide",
    )

    normalized_answer = _normalize_text(answer_text)

    # Normalize indicators the same way we normalize the answer so that
    # contractions like "don't" -> "don t" still match.
    normalized_indicators = tuple(_normalize_text(ind) for ind in abstain_indicators)
    normalized_negation_phrases = tuple(_normalize_text(p) for p in negation_phrases)

    detected = any(ind in normalized_answer for ind in normalized_indicators)

    if not detected:
        detected = any(phrase in normalized_answer for phrase in normalized_negation_phrases)

    if not detected:
        for claim in case.forbidden_claims:
            normalized_claim = _normalize_text(claim)
            simple_patterns = [
                f"not {normalized_claim}",
                f"{normalized_claim} is not",
                f"{normalized_claim} was not",
                f"{normalized_claim} are not",
                f"no {normalized_claim}",
                f"does not {normalized_claim}",
                f"doesn't {normalized_claim}",
                f"not contain {normalized_claim}",
                f"not include {normalized_claim}",
                f"lacks {normalized_claim}",
            ]
            if any(p in normalized_answer for p in simple_patterns):
                detected = True
                break

    return {"expected_abstain": True, "detected_abstain": detected, "passed": detected}


# Backward-compat alias (Phase 7/8 tests import this name)
check_abstention_behavior = check_abstention_behavior_enhanced


def check_source_alignment(
    answer_text: str,
    retrieved_titles: tuple[str, ...],
) -> dict:
    """Basic citation alignment: check cited title names appear in retrieved sources."""
    lower_text = answer_text.lower()
    mentioned = [
        t for t in retrieved_titles
        if t.lower() in lower_text
        or any(w.lower() in lower_text for w in t.split() if len(w) > 2)
    ]
    return {
        "retrieved_titles": list(retrieved_titles),
        "mentioned_in_answer": mentioned,
        "citation_coverage": (
            len(mentioned) / len(retrieved_titles) if retrieved_titles else 1.0
        ),
    }


# ---------------------------------------------------------------------------
# Aggregate evaluator
# ---------------------------------------------------------------------------


def evaluate_case(
    case: RAGEvaluationCase,
    answer_text: str,
    retrieved_titles: tuple[str, ...],
) -> dict[str, Any]:
    point_result = check_answer_points(answer_text, case.expected_answer_points)
    forbidden_result = check_forbidden_claims_enhanced(answer_text, case.forbidden_claims)
    abstain_result = check_abstention_behavior_enhanced(answer_text, case)
    alignment_result = check_source_alignment(answer_text, retrieved_titles)

    passed = (
        point_result["score"] >= 0.5
        and forbidden_result["passed"]
        and (not case.unanswerable or abstain_result["detected_abstain"])
    )

    return {
        "case_id": case.case_id,
        "category": case.category,
        "answer_category": case.answer_category,
        "expected_points_result": point_result,
        "forbidden_result": forbidden_result,
        "abstention_result": abstain_result,
        "source_alignment_result": alignment_result,
        "passed": passed,
    }
