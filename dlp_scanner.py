"""
dlp_scanner.py
--------------
Data Leakage Prevention scanner.
Uses regex patterns to detect sensitive data and prompt injection attempts
in user inputs before they reach the LLM.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScanResult:
    is_safe: bool
    category: Optional[str]
    matched_pattern: Optional[str]
    warning_message: str


# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

PATTERNS = {

    # --- Passwords ---
    "password": [
        r"(?i)(password|passwd|pwd|p@ss|p4ss|pass)\s*[=:is\s]+\s*\S+",
        r"(?i)my\s+(password|pwd|pass)\s+is\s+\S+",
        r"(?i)(password|pwd)\s*[:=]\s*\S+",
        r"[A-Za-z0-9@#$%^&*]{6,}!+",          # Typical strong password pattern
        r"p[-@]s{1,2}w[0o]rd",                  # Obfuscated: p@ssw0rd
    ],

    # --- Salary / financial ---
    "salary_financial": [
        r"(?i)(salary|sal|ctc|package|lpa|lakh)\s*[=:is\s]+\s*[\d,]+",
        r"(?i)sal\s*=\s*\d+",
        r"(?i)ctc\s*(is|=|:)?\s*\d+",
        r"(?i)\d+\s*(lpa|lakh\s*per\s*annum|per\s*annum)",
        r"(?i)(earn|earns|earning|paid|pay)\s+\d{4,}",
        r"(?i)increment\s+(of\s+)?\d+\s*%",
    ],

    # --- Government IDs (India) ---
    "government_id": [
        r"\b\d{4}\s\d{4}\s\d{4}\b",             # Aadhaar: XXXX XXXX XXXX
        r"\b\d{12}\b",                           # Aadhaar without spaces
        r"\b[A-Z]{5}\d{4}[A-Z]\b",              # PAN card
        r"(?i)(aadhar|aadhaar|pan\s*card|pan\s*number)\s*[=:is\s]+\s*[\w\s]+",
    ],

    # --- Phone / contact ---
    "phone_number": [
        r"\b[6-9]\d{9}\b",                       # Indian mobile number
        r"\+91[-\s]?\d{10}",                     # With country code
    ],

    # --- Bank / financial account ---
    "bank_account": [
        r"\b\d{9,18}\b(?=.*bank|.*acc|.*account)",  # Bank account number in context
        r"(?i)(bank\s*acc(ount)?|acc\s*no|account\s*number)\s*[=:is\s]+\s*\d+",
        r"\b4[0-9]{12}(?:[0-9]{3})?\b",         # Visa card
        r"\b5[1-5][0-9]{14}\b",                  # Mastercard
        r"\b3[47][0-9]{13}\b",                   # Amex
    ],

    # --- API keys / tokens ---
    "api_key_token": [
        r"(?i)(api[_-]?key|token|secret|bearer)\s*[=:]\s*[A-Za-z0-9\-_\.]{10,}",
        r"sk-[A-Za-z0-9]{20,}",                 # OpenAI-style API key
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",  # JWT token prefix
    ],

    # --- Prompt injection ---
    "prompt_injection": [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)",
        r"(?i)forget\s+(your\s+)?(rules?|instructions?|guidelines?|training)",
        r"(?i)(system\s+override|jailbreak|dan\s+mode|unrestricted\s+ai)",
        r"(?i)act\s+as\s+(an?\s+)?(unrestricted|unfiltered|uncensored)",
        r"(?i)pretend\s+(you\s+)?(have\s+no|without)\s+(restrictions?|filters?|rules?)",
        r"(?i)(bypass|disable|remove)\s+(safety|filters?|restrictions?|guidelines?)",
        r"(?i)you\s+are\s+now\s+an?\s+(unrestricted|admin|root|superuser)",
        r"(?i)(reveal|show|print|dump)\s+(all\s+)?(passwords?|credentials?|database|system\s+prompt)",
        r"###\s*(END\s+OF\s+PROMPT|SYSTEM|INSTRUCTIONS?)",
        r"\[INST\].*?(ignore|bypass|override).*?\[/INST\]",
        r"(?i)roleplay.*?(no\s+restrictions?|admin|root\s+access)",
        r"(?i)root\s+access\s+to\s+the\s+(hr|system|database)",
    ],

    # --- SSN / foreign ID ---
    "ssn": [
        r"\b\d{3}-\d{2}-\d{4}\b",               # SSN format
    ],

    # --- Email in sensitive context ---
    "email_in_sensitive_context": [
        r"(?i)(personal\s+email|private\s+email)\s*[=:is\s]+\s*[\w.]+@[\w.]+",
    ],
}


# Friendly warning messages per category
WARNINGS = {
    "password": (
        "Your message appears to contain a password or credential. "
        "Please never share passwords in chat. "
        "Use the IT helpdesk portal to reset or manage passwords safely."
    ),
    "salary_financial": (
        "Your message contains salary or financial information. "
        "For payroll queries, please contact HR at hr@company.com or raise a ticket through the HR portal."
    ),
    "government_id": (
        "Your message seems to contain a government ID (like Aadhaar or PAN). "
        "Please do not share personal IDs in chat. Submit them securely through the HR onboarding portal."
    ),
    "phone_number": (
        "Your message contains what looks like a phone number. "
        "If you need to update contact details, please do so through the employee self-service portal."
    ),
    "bank_account": (
        "Your message appears to contain bank account or card details. "
        "Never share financial account information in chat. Contact the finance team directly and securely."
    ),
    "api_key_token": (
        "Your message contains what looks like an API key or access token. "
        "Never share credentials in chat. Rotate the key immediately if it was accidentally exposed."
    ),
    "prompt_injection": (
        "Your message looks like an attempt to override the chatbot's instructions. "
        "This type of input is not allowed. Please ask a genuine work-related question."
    ),
    "ssn": (
        "Your message appears to contain a Social Security Number or similar ID. "
        "Please do not share personal identifiers in chat."
    ),
    "email_in_sensitive_context": (
        "Your message contains personal contact information. "
        "Please update your details through the HR self-service portal instead."
    ),
}


def scan(user_input: str) -> ScanResult:
    """
    Scan a user input string for sensitive data or injection attempts.
    Returns a ScanResult indicating whether the input is safe to process.
    """
    text = user_input.strip()

    for category, pattern_list in PATTERNS.items():
        for pattern in pattern_list:
            if re.search(pattern, text):
                return ScanResult(
                    is_safe=False,
                    category=category,
                    matched_pattern=pattern,
                    warning_message=WARNINGS.get(
                        category,
                        "Your message contains potentially sensitive content and has been blocked."
                    ),
                )

    return ScanResult(
        is_safe=True,
        category=None,
        matched_pattern=None,
        warning_message="",
    )


def get_category_label(category: str) -> str:
    """Return a human-readable label for a detection category."""
    labels = {
        "password": "Password / credential",
        "salary_financial": "Salary / financial data",
        "government_id": "Government ID",
        "phone_number": "Phone number",
        "bank_account": "Bank / card details",
        "api_key_token": "API key / token",
        "prompt_injection": "Prompt injection attempt",
        "ssn": "SSN / personal ID",
        "email_in_sensitive_context": "Personal contact info",
    }
    return labels.get(category, category.replace("_", " ").title())