"""Metadata extraction from document segments."""

from __future__ import annotations

import logging
import re
from datetime import datetime

import spacy

from ..models.document import DocumentSegment

logger = logging.getLogger(__name__)
import textacy.extract  # noqa: E402


class MetadataExtractor:
    """Extracts structured metadata from document segments."""

    def __init__(self, spacy_model: str = "en_core_web_sm"):
        """Initialize metadata extractor.

        Args:
            spacy_model: spaCy model to use for NLP processing
        """
        # Add config attribute for test compatibility
        try:
            from ..utils.config import get_config

            self.config = get_config()
        except ImportError:
            # Fallback for test environments
            self.config = type("Config", (), {})()

        try:
            self.nlp = spacy.load(spacy_model)
        except OSError:
            logger.error(
                f"spaCy model '{spacy_model}' not found. Please download it by running 'python -m spacy download {spacy_model}'"
            )
            raise
        self.document_type_keywords = self._build_document_type_keywords()

    def extract_metadata(
        self, segments: list[DocumentSegment]
    ) -> list[DocumentSegment]:
        """Extract metadata from document segments.

        Args:
            segments: List of document segments

        Returns:
            List of segments with extracted metadata
        """
        enriched_segments = []
        for segment in segments:
            # Extract dates
            segment.date_of_service = self._extract_date(segment.text_content)
            # Extract document type
            segment.document_type = self._extract_document_type(segment.text_content)
            # Extract provider and facility information
            providers = self._extract_providers(segment.text_content)
            segment.provider_name = providers.get("provider")
            segment.facility_name = providers.get("facility")
            # Extract keywords
            segment.keywords = self._extract_keywords(segment.text_content)
            enriched_segments.append(segment)
        return enriched_segments

    def _extract_date(self, text: str) -> datetime | None:
        """Extract date of service from text.

        Args:
            text: Text to extract date from

        Returns:
            Extracted datetime or None
        """
        # Date patterns in order of preference
        date_patterns = [
            r"Date of Service:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"Service Date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"DOS:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"Date:\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",  # Any date pattern
        ]
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1)
                try:
                    # Try different date formats
                    for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"]:
                        try:
                            return datetime.strptime(date_str, fmt)
                        except ValueError:
                            continue
                except ValueError:
                    continue
        # Fallback to spaCy date extraction
        doc = self.nlp(text[:1000])  # Limit text for performance
        for ent in doc.ents:
            if ent.label_ == "DATE":
                try:
                    # Simple date parsing for common formats
                    date_text = ent.text
                    if re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", date_text):
                        for fmt in ["%m/%d/%Y", "%m-%d-%Y", "%m/%d/%y", "%m-%d-%y"]:
                            try:
                                return datetime.strptime(date_text, fmt)
                            except ValueError:
                                continue
                except ValueError:
                    continue
        return None

    def _extract_document_type(self, text: str) -> str | None:
        """Extract document type from text.

        Args:
            text: Text to extract document type from

        Returns:
            Document type or None
        """
        text_lower = text.lower()
        # Check for exact keyword matches
        for doc_type, keywords in self.document_type_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return doc_type
        # Check for all-caps headers (likely document types)
        lines = text.split("\n")[:10]  # Check first 10 lines
        for line in lines:
            line = line.strip()
            if len(line) > 5 and line.isupper() and not line.isdigit():
                # Clean up the header
                cleaned = re.sub(r"[^A-Z\s]", "", line).strip()
                if cleaned:
                    return cleaned.title()
        return None

    def _extract_providers(self, text: str) -> dict[str, str | None]:
        """Extract provider and facility information.

        Args:
            text: Text to extract provider info from

        Returns:
            Dictionary with provider and facility information
        """
        providers = {"provider": None, "facility": None}
        # Pattern-based extraction
        provider_patterns = [
            r"Provider:\s*(.+?)(?:\n|$)",
            r"Physician:\s*(.+?)(?:\n|$)",
            r"Doctor:\s*(.+?)(?:\n|$)",
            r"Attending:\s*(.+?)(?:\n|$)",
            r"MD:\s*(.+?)(?:\n|$)",
        ]
        facility_patterns = [
            r"Facility:\s*(.+?)(?:\n|$)",
            r"Hospital:\s*(.+?)(?:\n|$)",
            r"Clinic:\s*(.+?)(?:\n|$)",
            r"Medical Center:\s*(.+?)(?:\n|$)",
        ]
        for pattern in provider_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                providers["provider"] = match.group(1).strip()
                break
        for pattern in facility_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                providers["facility"] = match.group(1).strip()
                break
        # NLP-based extraction as fallback
        if not providers["provider"] or not providers["facility"]:
            doc = self.nlp(text[:1000])  # Limit text for performance
            for ent in doc.ents:
                if ent.label_ == "PERSON" and not providers["provider"]:
                    # Check if it looks like a doctor's name
                    if re.search(r"\b(dr|doctor|md)\b", ent.text, re.IGNORECASE):
                        providers["provider"] = ent.text
                elif ent.label_ == "ORG" and not providers["facility"]:
                    # Check if it looks like a medical facility
                    if re.search(
                        r"\b(hospital|clinic|medical|center|health)\b",
                        ent.text,
                        re.IGNORECASE,
                    ):
                        providers["facility"] = ent.text
        return providers

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from text.

        Args:
            text: Text to extract keywords from

        Returns:
            List of extracted keywords
        """
        # Pre-filter text to remove likely garbled content
        filtered_text = self._filter_text_for_keywords(text)

        try:
            doc = textacy.make_spacy_doc(filtered_text, lang=self.nlp)
            keywords = textacy.extract.keyterms.sgrank(doc, topn=15)

            # Filter keywords to remove garbled text
            valid_keywords = []
            for kw, _score in keywords:
                if self._is_valid_keyword(kw):
                    valid_keywords.append(kw)

            return valid_keywords[:10]  # Return top 10 valid keywords
        except Exception as e:
            logger.warning(f"Keyword extraction failed: {e}")
            return []

    def _filter_text_for_keywords(self, text: str) -> str:
        """Filter text to improve keyword extraction quality.

        Args:
            text: Raw text

        Returns:
            Filtered text suitable for keyword extraction
        """
        import re

        # Remove page markers
        text = re.sub(r"\[PAGE_\d+\]", "", text)

        # Remove lines that are mostly non-alphabetic
        lines = text.split("\n")
        filtered_lines = []
        for line in lines:
            # Keep lines that have at least 50% alphabetic characters
            alpha_chars = len(re.sub(r"[^a-zA-Z]", "", line))
            if len(line) > 0 and alpha_chars / len(line) >= 0.5:
                filtered_lines.append(line)

        return "\n".join(filtered_lines)

    def _is_valid_keyword(self, keyword: str) -> bool:
        """Check if a keyword is valid (not garbled text).

        Args:
            keyword: Potential keyword

        Returns:
            True if keyword appears valid
        """
        import re

        # Basic filters
        if len(keyword) < 3 or len(keyword) > 30:
            return False

        # Must be mostly alphabetic
        alpha_chars = len(re.sub(r"[^a-zA-Z]", "", keyword))
        if alpha_chars / len(keyword) < 0.7:
            return False

        # Reject keywords with repeated characters (likely artifacts)
        if re.search(r"(.)\1{2,}", keyword):
            return False

        # Reject keywords with too many special characters
        special_chars = len(re.sub(r"[a-zA-Z0-9\s]", "", keyword))
        if special_chars > len(keyword) * 0.3:
            return False

        # Medical/legal terms are more likely to be valid
        medical_indicators = [
            "patient",
            "diagnosis",
            "treatment",
            "doctor",
            "hospital",
            "medical",
            "clinical",
            "therapy",
            "medication",
            "examination",
            "record",
            "report",
            "history",
            "service",
            "provider",
            "clinic",
            "visit",
            "care",
            "health",
        ]
        if any(indicator in keyword.lower() for indicator in medical_indicators):
            return True

        # Common English words are likely valid
        common_words = [
            "the",
            "and",
            "for",
            "with",
            "from",
            "this",
            "that",
            "will",
            "have",
            "been",
            "were",
            "said",
            "each",
            "which",
            "their",
            "time",
            "day",
            "may",
            "use",
            "her",
            "would",
            "there",
            "one",
            "all",
        ]
        if keyword.lower() in common_words:
            return False  # Too common to be useful

        return True

    def _build_document_type_keywords(self) -> dict[str, list[str]]:
        """Build document type keyword mapping.

        Returns:
            Dictionary mapping document types to keyword lists
        """
        return {
            "Admission Note": ["admission", "admit", "admission note"],
            "Discharge Summary": ["discharge", "discharge summary", "discharge note"],
            "Progress Note": ["progress", "progress note", "daily note"],
            "Consultation": ["consultation", "consult", "referral"],
            "Operative Report": ["operative", "surgery", "procedure", "operation"],
            "Laboratory Results": ["lab", "laboratory", "lab results", "blood work"],
            "Radiology Report": ["radiology", "x-ray", "ct", "mri", "ultrasound"],
            "Pathology Report": ["pathology", "biopsy", "specimen"],
            "Emergency Department": ["emergency", "ed", "er", "emergency department"],
            "Nursing Note": ["nursing", "nurse", "nursing note"],
            "Medication List": ["medication", "drug", "prescription", "pharmacy"],
            "Vital Signs": ["vital signs", "vitals", "temperature", "blood pressure"],
        }
