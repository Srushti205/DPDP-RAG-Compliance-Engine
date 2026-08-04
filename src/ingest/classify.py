"""Document type classification using keyword-frequency scoring.

Classifies a hotel document into one of several DPDP-relevant categories
based on the presence of domain-specific vocabulary in the cleaned text.
No LLM or ML model is used — pure deterministic keyword matching.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentType(str, Enum):
    """DPDP-relevant hotel document categories."""

    PRIVACY_POLICY = "privacy_policy"
    CONSENT_FORM = "consent_form"
    GUEST_REGISTRATION = "guest_registration"
    DATA_PROCESSING_AGREEMENT = "data_processing_agreement"
    EMPLOYEE_AGREEMENT = "employee_agreement"
    VENDOR_CONTRACT = "vendor_contract"
    SECURITY_POLICY = "security_policy"
    INCIDENT_RESPONSE = "incident_response"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ClassificationResult:
    """Outcome of document classification."""

    document_type: DocumentType
    confidence: float  # 0.0 – 1.0
    matched_keywords: list[str]


# Keyword sets per document type — order matters: first match wins on tie
_KEYWORD_MAP: dict[DocumentType, list[str]] = {
    DocumentType.PRIVACY_POLICY: [
        "privacy policy",
        "personal data",
        "data subject",
        "data controller",
        "data processor",
        "right to erasure",
        "right to access",
        "consent withdrawal",
        "data retention",
        "privacy notice",
    ],
    DocumentType.CONSENT_FORM: [
        "i consent",
        "i agree to",
        "consent to processing",
        "explicit consent",
        "opt-in",
        "opt in",
        "freely given",
        "withdraw consent",
        "informed consent",
    ],
    DocumentType.GUEST_REGISTRATION: [
        "check-in",
        "check in",
        "guest registration",
        "passport number",
        "nationality",
        "date of arrival",
        "date of departure",
        "room number",
        "reservation",
    ],
    DocumentType.DATA_PROCESSING_AGREEMENT: [
        "data processing agreement",
        "dpa",
        "sub-processor",
        "data importer",
        "data exporter",
        "standard contractual clauses",
        "processor obligations",
    ],
    DocumentType.EMPLOYEE_AGREEMENT: [
        "employment agreement",
        "employee",
        "staff member",
        "non-disclosure",
        "confidentiality obligation",
        "data handling training",
        "code of conduct",
    ],
    DocumentType.VENDOR_CONTRACT: [
        "vendor",
        "supplier",
        "service provider",
        "third party",
        "indemnification",
        "liability clause",
        "scope of services",
    ],
    DocumentType.SECURITY_POLICY: [
        "information security policy",
        "access control",
        "encryption",
        "firewall",
        "vulnerability",
        "penetration test",
        "security incident",
        "iso 27001",
    ],
    DocumentType.INCIDENT_RESPONSE: [
        "incident response",
        "data breach",
        "breach notification",
        "root cause analysis",
        "containment",
        "remediation plan",
        "72 hours",
    ],
}


def classify_document(text: str) -> ClassificationResult:
    """Classify a document by scoring keyword frequencies in *text*.

    Args:
        text: Cleaned full document text.

    Returns:
        A :class:`ClassificationResult` with the best-match type, a
        normalised confidence score, and the list of matched keywords.
    """
    lower = text.lower()
    scores: dict[DocumentType, list[str]] = {}

    for doc_type, keywords in _KEYWORD_MAP.items():
        matched = [kw for kw in keywords if re.search(re.escape(kw), lower)]
        if matched:
            scores[doc_type] = matched

    if not scores:
        logger.info("Classification: UNKNOWN (no keywords matched)")
        return ClassificationResult(
            document_type=DocumentType.UNKNOWN,
            confidence=0.0,
            matched_keywords=[],
        )

    best_type = max(scores, key=lambda dt: len(scores[dt]))
    matched = scores[best_type]
    pool_size = len(_KEYWORD_MAP[best_type])
    confidence = round(min(len(matched) / pool_size, 1.0), 4)

    logger.info(
        "Classification: %s  confidence=%.2f  matched=%d/%d",
        best_type.value,
        confidence,
        len(matched),
        pool_size,
    )
    return ClassificationResult(
        document_type=best_type,
        confidence=confidence,
        matched_keywords=matched,
    )
