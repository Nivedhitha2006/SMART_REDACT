"""
redactor.py — Core redaction pipeline
Handles spaCy NER + regex pattern matching
Kept separate from Flask routes for clean architecture
"""

import re
import spacy

# Load spaCy model once at module level (not per-request)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    raise RuntimeError(
        "spaCy model not found. Run: python -m spacy download en_core_web_sm"
    )


# ──────────────────────────────────────────────
# Regex Patterns
# ──────────────────────────────────────────────
PATTERNS = {
    "EMAIL": re.compile(
        r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
        re.IGNORECASE,
    ),
    "PHONE": re.compile(
        r"(?:\+91[\s\-]?)?[6-9]\d{9}\b"
    ),
    "AADHAAR": re.compile(
        r"\b[2-9]\d{3}\s?\d{4}\s?\d{4}\b"
    ),
    "PAN": re.compile(
        r"\b[A-Z]{5}[0-9]{4}[A-Z]\b"
    ),
    # Catches names after closing words — allows single-letter surnames like "K"
    "NAME_CLOSING": re.compile(
        r'(?:^|\n)(?:Regards|Sincerely|Thanks|From|Yours truly|Warm regards)[,\n]+\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?){1,3})',
        re.MULTILINE
    ),
}

# Catches names after salutations — allows single-letter surnames like "K"
# e.g. "Dear Nivedhitha K," or "Dear Priya Venkataraman,"
SALUTATION_PATTERN = re.compile(
    r'\b(?:Dear|Mr\.?|Mrs\.?|Ms\.?|Dr\.?|Prof\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?){0,3})',
    re.MULTILINE
)

# Catches standalone name at the very top of a CV or letter
# e.g. "Nivedhitha K" sitting alone on its own line in the first 300 chars
HEADER_NAME_PATTERN = re.compile(
    r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]*\.?){1,3})\s*$',
    re.MULTILINE
)

# City / state / common words to skip so header pattern doesn't falsely fire
HEADER_SKIP_WORDS = {
    "Tamil Nadu", "Andhra Pradesh", "West Bengal", "Uttar Pradesh",
    "Madhya Pradesh", "Himachal Pradesh", "Arunachal Pradesh",
    "Dear Hiring", "The HR", "Hiring Manager", "Subject Application",
    "India", "Chennai", "Mumbai", "Delhi", "Bangalore", "Hyderabad",
    "Kolkata", "Pune", "Ahmedabad", "Jaipur", "Lucknow", "Surat",
}


def redact_text(text: str, enabled_types: set | None = None) -> dict:
    """
    Run the full redaction pipeline on input text.

    Args:
        text: Raw input text to redact
        enabled_types: Set of entity type strings to redact.
                       If None, all types are redacted.

    Returns:
        {
          "redacted_text": str,
          "highlighted_html": str,
          "summary": {"NAME": int, "EMAIL": int, ...}
        }
    """
    if enabled_types is None:
        enabled_types = {"NAME", "EMAIL", "PHONE", "AADHAAR", "PAN"}

    summary = {k: 0 for k in ["NAME", "EMAIL", "PHONE", "AADHAAR", "PAN"]}

    spans = []  # list of [start, end, label, original_text]

    # ── 1. spaCy NER for PERSON names ─────────────────────────────────────
    if "NAME" in enabled_types:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                spans.append([ent.start_char, ent.end_char, "NAME", ent.text])

        # Fallback 1 — salutation names spaCy misses
        # e.g. "Dear Nivedhitha K," or "Mr. Rajesh Kumar"
        for m in SALUTATION_PATTERN.finditer(text):
            spans.append([m.start(1), m.end(1), "NAME", m.group(1)])

        # Fallback 2 — standalone name at top of document (CV / letter header)
        # Only scan first 300 characters to avoid false positives mid-document
        header_section = text[:300]
        for m in HEADER_NAME_PATTERN.finditer(header_section):
            name = m.group(1)
            # Must have at least 2 words and not be a city/state name
            if name not in HEADER_SKIP_WORDS and len(name.split()) >= 2:
                spans.append([m.start(1), m.end(1), "NAME", name])

    # ── 2. Regex patterns ─────────────────────────────────────────────────
    for label, pattern in PATTERNS.items():
        # NAME_CLOSING is a sub-type of NAME
        if label == "NAME_CLOSING":
            if "NAME" not in enabled_types:
                continue
        else:
            if label not in enabled_types:
                continue

        actual_label = "NAME" if label == "NAME_CLOSING" else label

        for m in pattern.finditer(text):
            if label == "NAME_CLOSING":
                # group(1) is just the name, not "Regards,\nNivedhitha K"
                spans.append([m.start(1), m.end(1), actual_label, m.group(1)])
            else:
                spans.append([m.start(), m.end(), actual_label, m.group()])

    # ── 3. Resolve overlapping spans ──────────────────────────────────────
    spans = _resolve_overlaps(spans)

    # ── 4. Sort descending so splicing from the end doesn't shift offsets ──
    spans.sort(key=lambda s: s[0], reverse=True)

    # ── 5. Build plain redacted text ──────────────────────────────────────
    redacted = text
    for start, end, label, _ in spans:
        redacted = redacted[:start] + f"[{label}]" + redacted[end:]
        summary[label] += 1

    # ── 6. Build colour-coded HTML ────────────────────────────────────────
    highlighted_html = _build_highlighted_html(
        text,
        sorted([[s[0], s[1], s[2], s[3]] for s in spans], key=lambda s: s[0])
    )

    return {
        "redacted_text": redacted,
        "highlighted_html": highlighted_html,
        "summary": summary,
    }


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

LABEL_COLORS = {
    "NAME":    "#FF6B6B",
    "EMAIL":   "#4ECDC4",
    "PHONE":   "#FFD93D",
    "AADHAAR": "#A855F7",
    "PAN":     "#22C55E",
}


def _resolve_overlaps(spans: list) -> list:
    """
    Remove overlapping spans.
    When two spans overlap keep the earlier one.
    If same start position keep the longer one.
    """
    if not spans:
        return spans

    spans.sort(key=lambda s: (s[0], -(s[1] - s[0])))
    resolved = [spans[0]]
    for span in spans[1:]:
        prev = resolved[-1]
        if span[0] >= prev[1]:
            resolved.append(span)
        elif (span[1] - span[0]) > (prev[1] - prev[0]):
            resolved[-1] = span
    return resolved


def _build_highlighted_html(original_text: str, spans_asc: list) -> str:
    """
    Build HTML with colour-coded marks showing what was redacted.
    Hover over any mark to see the original value.
    """
    result_parts = []
    cursor = 0

    for start, end, label, original in spans_asc:
        if cursor < start:
            result_parts.append(_escape_html(original_text[cursor:start]))
        color = LABEL_COLORS.get(label, "#ccc")
        result_parts.append(
            f'<mark class="redact-mark" '
            f'style="background:{color}22; border-bottom: 2px solid {color}; '
            f'color:{color}; border-radius:3px; padding:1px 4px;" '
            f'title="Original: {_escape_html(original)}">'
            f'[{label}]</mark>'
        )
        cursor = end

    if cursor < len(original_text):
        result_parts.append(_escape_html(original_text[cursor:]))

    return "".join(result_parts).replace("\n", "<br>")


def _escape_html(text: str) -> str:
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )