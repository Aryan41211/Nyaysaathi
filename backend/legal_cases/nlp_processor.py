"""
nlp_processor.py – NyaySaathi NLP Query Understanding Engine
=============================================================

Sits BETWEEN raw user input and the TF-IDF search engine.

Pipeline:
  User raw text (any language, messy)
      ↓
  Claude API (NLP processing prompt)
      ↓
  Structured JSON: normalized_query, keywords, problem_domain, etc.
      ↓
  TF-IDF search on search_ready_query + keywords
      ↓
  Results

Falls back gracefully to raw query if Claude API is unavailable or
ANTHROPIC_API_KEY is not set.
"""

import json
import logging
import os
import re
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

# ── System prompt (from NyaySaathi NLP spec) ─────────────────────────────

NLP_SYSTEM_PROMPT = """You are the NLP query understanding engine of NyaySaathi.

NyaySaathi is an AI legal procedural navigation system that maps user problems to one of 201 structured legal cases stored in the database.

Your role is NOT to give legal advice.
Your role is to convert messy human input into a clean structured query that can be matched against the NyaySaathi dataset.

SYSTEM CONTEXT:
The database contains these categories:
• Land and Property Disputes
• Labour and Wage Issues
• Domestic Violence and Family Disputes
• Cyber Fraud and Digital Scams
• Consumer Complaints
• Police Complaints and Local Crime
• Government Scheme and Public Service Issues
• Tenant–Landlord Disputes
• Environmental and Public Nuisance Complaints
• Senior Citizen Protection Issues

INPUT CHARACTERISTICS
User input may contain: English, Hindi, Marathi, Hinglish, Manglish, mixed sentences.
User may also have: spelling mistakes, typing errors, grammar mistakes, voice typing errors, informal writing, emotional writing, very short or very long queries.
You must understand MEANING, not grammar.

STEP 1 — LANGUAGE DETECTION
Detect: English / Hindi / Marathi / Mixed

STEP 2 — TEXT NORMALIZATION
Fix spelling mistakes:
  salry → salary | polce → police | fir → FIR | compaint → complaint | fraudupii → UPI fraud
Normalize Hinglish: "mera salary nahi mila" → "salary not paid"
Normalize Marathi phonetics: "polis complaint ghet nahi" → "police FIR refusal"
Remove noise words: "please help", "urgent", "sir", "problem"
Keep problem meaning only.

STEP 3 — INTENT EXTRACTION
Extract main legal issue, secondary issue, actor involved (citizen vs employer/landlord/police/bank/government), problem domain.

STEP 4 — KEYWORD GENERATION
Generate 5–10 clean English keywords for search engine.
Example: "UPI fraud paisa gaya" → ["upi fraud", "cyber crime", "online payment fraud", "bank complaint", "digital scam"]

STEP 5 — QUERY REWRITE
Rewrite user query into clean English search query.
"mera boss paisa nahi de raha" → "Employer not paying salary"
"police FIR nahi le rahe" → "Police refusing to register FIR"

STEP 6 — DATASET MATCH PREPARATION
DO NOT choose final case. DO NOT explain law. DO NOT give IPC sections. DO NOT give advice.
Only prepare the query. You are the preprocessing layer.

If user writes a story, extract only the core problem.
If multiple issues, pick the primary problem.

OUTPUT FORMAT — return ONLY valid JSON, no other text, no markdown:
{
  "detected_language": "",
  "normalized_query": "",
  "keywords": [],
  "problem_domain": "",
  "problem_type": "",
  "likely_authority": "",
  "search_ready_query": "",
  "confidence": ""
}

CONFIDENCE RULE:
  High   = clear problem statement
  Medium = some ambiguity
  Low    = unclear issue"""


def _call_claude_api(user_query: str) -> dict | None:
    """
    Call the Anthropic Claude API directly via urllib (no SDK required).
    Returns parsed NLP JSON or None on any failure.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.debug("ANTHROPIC_API_KEY not set — skipping NLP processing")
        return None

    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",   # fast + cheap for preprocessing
        "max_tokens": 512,
        "system": NLP_SYSTEM_PROMPT,
        "messages": [
            {"role": "user", "content": user_query}
        ]
    }).encode("utf-8")

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode("utf-8"))

        # Extract text from response
        text = ""
        for block in body.get("content", []):
            if block.get("type") == "text":
                text += block.get("text", "")

        # Parse JSON from response
        # Strip any accidental markdown fences
        text = re.sub(r"```(?:json)?", "", text).strip()
        parsed = json.loads(text)

        # Validate required keys
        required = {"detected_language", "normalized_query", "keywords",
                    "problem_domain", "problem_type", "likely_authority",
                    "search_ready_query", "confidence"}
        if not required.issubset(parsed.keys()):
            logger.warning("NLP response missing keys: %s", required - parsed.keys())
            return None

        logger.info("NLP processed: lang=%s domain=%s confidence=%s",
                    parsed.get("detected_language"),
                    parsed.get("problem_domain"),
                    parsed.get("confidence"))
        return parsed

    except urllib.error.URLError as e:
        logger.warning("Claude API network error: %s", e)
        return None
    except json.JSONDecodeError as e:
        logger.warning("Claude API returned non-JSON: %s", e)
        return None
    except Exception as e:
        logger.warning("Claude API unexpected error: %s", e)
        return None


def _fallback_process(raw_query: str) -> dict:
    """
    Rule-based fallback when Claude API is unavailable.
    Handles common Hinglish / Hindi transliteration patterns.
    """
    q = raw_query.lower().strip()

    # Common Hinglish → English mappings
    replacements = {
        r"\bmera\b|\bhamara\b|\bmeri\b":       "",
        r"\bnahi\b|\bnai\b|\bnahi[n]?\b":      "not",
        r"\bmila\b|\bnahi mila\b":             "not received",
        r"\bde raha nahi\b|\bnahi de raha\b":  "not paying",
        r"\bkar raha\b":                       "doing",
        r"\bpaisa\b|\bpaise\b":                "money",
        r"\bboss\b|\bmalik\b|\bmalak\b":       "employer",
        r"\bghar\b|\bmakaaan\b|\bmakan\b":     "house",
        r"\bzameen\b|\bjamin\b|\bzemin\b":     "land",
        r"\bpolis\b|\bpolice\b":               "police",
        r"\bchori\b":                          "theft",
        r"\bdharkan\b|\bpita\b|\bpati\b":      "husband",
        r"\bkiraya\b|\bkiaya\b":               "rent",
        r"\bdukaan\b":                         "shop",
        r"\bsalry\b|\bsalary\b":               "salary",
        r"\bkam\b|\bkaam\b":                   "work",
        r"\bcompaint\b|\bcomplaint\b":         "complaint",
        r"\bfraud\b|\bdhokha\b|\bthagi\b":     "fraud",
        r"\bsir\b|\bplease\b|\bhelp\b|\burgent\b|\bproblem\b": "",
    }

    cleaned = q
    for pattern, replacement in replacements.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)

    # Remove extra whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    search_query = cleaned if cleaned else raw_query

    return {
        "detected_language":  "Mixed" if re.search(r"[^\x00-\x7F]|mera|nahi|paisa|boss|ghar", q) else "English",
        "normalized_query":   search_query,
        "keywords":           search_query.split()[:8],
        "problem_domain":     "Unknown",
        "problem_type":       "General",
        "likely_authority":   "Unknown",
        "search_ready_query": search_query,
        "confidence":         "Low",
        "nlp_source":         "fallback",
    }


def process_query(raw_query: str) -> dict:
    """
    Main entry point.
    
    1. Try Claude API NLP processing.
    2. Fall back to rule-based processing if API unavailable.
    3. Always return a dict with at least search_ready_query and keywords.

    The returned dict is used by search_cases() to build the final search string.
    """
    if not raw_query or not raw_query.strip():
        return {
            "detected_language":  "Unknown",
            "normalized_query":   "",
            "keywords":           [],
            "problem_domain":     "",
            "problem_type":       "",
            "likely_authority":   "",
            "search_ready_query": "",
            "confidence":         "Low",
            "nlp_source":         "empty",
        }

    # Try Claude API
    result = _call_claude_api(raw_query)

    if result:
        result["nlp_source"] = "claude"
        result["original_query"] = raw_query
        return result

    # Fallback
    result = _fallback_process(raw_query)
    result["original_query"] = raw_query
    return result


def build_enhanced_search_string(nlp_result: dict, raw_query: str) -> str:
    """
    Combine NLP outputs into a single enriched search string for TF-IDF.
    
    Strategy:
      - search_ready_query (highest weight — repeat 3x)
      - keywords joined (medium weight — repeat 2x)
      - normalized_query (base — 1x)
    
    Repetition increases TF-IDF weight of NLP-extracted terms naturally.
    """
    parts = []

    search_ready = nlp_result.get("search_ready_query", "").strip()
    keywords     = nlp_result.get("keywords", [])
    normalized   = nlp_result.get("normalized_query", "").strip()
    domain       = nlp_result.get("problem_domain", "").strip()
    prob_type    = nlp_result.get("problem_type", "").strip()

    if search_ready:
        parts += [search_ready] * 3   # highest weight

    if keywords:
        kw_string = " ".join(str(k) for k in keywords if k)
        parts += [kw_string] * 2      # medium weight

    if normalized and normalized != search_ready:
        parts.append(normalized)      # base weight

    if domain:
        parts.append(domain)

    if prob_type:
        parts.append(prob_type)

    # Always include raw query as safety net
    parts.append(raw_query)

    return " ".join(parts)
