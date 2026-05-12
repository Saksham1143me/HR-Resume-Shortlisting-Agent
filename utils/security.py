"""
utils/security.py — Security utilities for the HR agent.

Covers:
  1. Prompt Injection Defense   — Sanitise user-supplied text before injecting into prompts
  2. PII Masking                — Hash/redact emails, phones in logs
  3. Input Validation           — File type whitelisting, size limits
  4. Output Validation          — Ensure LLM output matches schema (anti-hallucination)

Security Mitigations (as required by the brief):
─────────────────────────────────────────────────
Risk                  │ Our Mitigation
──────────────────────┼──────────────────────────────────────────────────────
Prompt Injection      │ strip_prompt_injection() removes control sequences and
                      │ special tokens before text enters any prompt template.
                      │ LLM responses are parsed via Pydantic — free-text fields
                      │ are never executed.
──────────────────────┼──────────────────────────────────────────────────────
Data Privacy / PII    │ mask_pii() replaces emails/phones with SHA-256 hashes
                      │ before writing to logs. Raw PII never appears in log files.
──────────────────────┼──────────────────────────────────────────────────────
API Key Exposure      │ Keys loaded via python-dotenv from .env (in .gitignore).
                      │ config.py validates presence at startup; no key in code.
──────────────────────┼──────────────────────────────────────────────────────
Hallucination Risk    │ All LLM outputs are parsed through Pydantic models.
                      │ Scores are clamped to [0, 10]; weights validated to sum=1.
                      │ Human-in-the-loop override available for every candidate.
──────────────────────┼──────────────────────────────────────────────────────
Unauthorised Access   │ Streamlit UI requires a session token (env-configured).
                      │ File uploads restricted to PDF/DOCX, max 10 MB each.
"""

import re
import hashlib
import hmac
from pathlib import Path
from typing import Optional
from loguru import logger

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

INJECTION_PATTERNS = [
    r"ignore (all |previous |above |prior )?instructions?",
    r"disregard (all |previous |above |prior )?instructions?",
    r"you are now",
    r"system prompt",
    r"<\|im_start\|>",     
    r"<\|im_end\|>",
    r"\[INST\]",             
    r"\[\/INST\]",
    r"<\|endoftext\|>",
    r"###\s*(system|user|assistant)\s*:",
    r"```\s*(system|prompt)\s*",
    r"act as (an? )?(?!candidate|applicant)",  
    r"jailbreak",
    r"DAN mode",
    r"developer mode",
]

_INJECTION_RE = re.compile(
    "|".join(INJECTION_PATTERNS),
    flags=re.IGNORECASE
)


_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(
    r"(\+?[\d\s\-().]{7,})"  
)


def _hmac_hash(value: str, secret: str) -> str:
    """HMAC-SHA256 hash for deterministic but non-reversible PII masking."""
    return hmac.new(
        secret.encode(),
        value.encode(),
        hashlib.sha256
    ).hexdigest()[:12]


def mask_pii(text: str, secret: Optional[str] = None) -> str:

    if secret is None:
        from utils.config import PII_MASK_SECRET
        secret = PII_MASK_SECRET

    def replace_email(m: re.Match) -> str:
        h = _hmac_hash(m.group(), secret)
        return f"[EMAIL:{h}]"

    def replace_phone(m: re.Match) -> str:
        digits = re.sub(r"\D", "", m.group())
        if len(digits) < 7:   # too short to be a real phone
            return m.group()
        h = _hmac_hash(digits, secret)
        return f"[PHONE:{h}]"

    text = _EMAIL_RE.sub(replace_email, text)
    text = _PHONE_RE.sub(replace_phone, text)
    return text


def strip_prompt_injection(text: str) -> str:
    MAX_SAFE_LENGTH = 50_000 
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    if _INJECTION_RE.search(text):
        logger.warning("Prompt injection pattern detected in input — sanitising.")
        text = _INJECTION_RE.sub("[REDACTED]", text)
    if len(text) > MAX_SAFE_LENGTH:
        logger.warning(f"Input truncated from {len(text)} to {MAX_SAFE_LENGTH} chars.")
        text = text[:MAX_SAFE_LENGTH] + "\n[TRUNCATED FOR SAFETY]"

    return text


def validate_upload_file(file_path: Path) -> tuple[bool, str]:

    if not file_path.exists():
        return False, f"File not found: {file_path}"

    ext = file_path.suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}"

    size = file_path.stat().st_size
    if size > MAX_FILE_SIZE_BYTES:
        return False, f"File too large ({size/1e6:.1f} MB). Max: {MAX_FILE_SIZE_BYTES/1e6:.0f} MB"

    if size == 0:
        return False, "File is empty."

    return True, ""


def sanitise_candidate_id(candidate_id: str) -> str:
    """Ensure candidate ID is safe for use in filenames and logs."""
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", candidate_id)[:64]