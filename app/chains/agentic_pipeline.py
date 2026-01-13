"""
═══════════════════════════════════════════════════════════════════════════════
                    AGENTIC DOCUMENT UNDERSTANDING PIPELINE
                    ─────────────────────────────────────────
                    Revolutionary Multi-Stage Extraction Engine
                    for Complex Credit Agreements (190+ pages)
═══════════════════════════════════════════════════════════════════════════════

Architecture:
    ┌─────────────────┐
    │  Stage 1: TOC   │  Document Structure Analysis
    │  Extraction     │  Extract Articles, Sections, Exhibits
    └────────┬────────┘
             ▼
    ┌─────────────────┐
    │  Stage 2:       │  Parallel Entity Extraction
    │  Entity Focus   │  Parties │ Facilities │ Dates │ Terms
    └────────┬────────┘
             ▼
    ┌─────────────────┐
    │  Stage 3:       │  Cross-Reference & Validate
    │  Reconciliation │  Merge, Dedupe, Verify
    └────────┬────────┘
             ▼
    ┌─────────────────┐
    │  Stage 4:       │  Self-Healing with Fallbacks
    │  Enrichment     │  Fill gaps with targeted queries
    └─────────────────┘

Key Features:
- Semantic Chunking: Split by actual document structure
- Entity-Focused Extraction: Dedicated passes for each data type
- Multi-Model Strategy: Fast model first, powerful model for complex sections
- Self-Healing: Automatic retry with different strategies on failure
- Confidence Scoring: Know when data is reliable vs uncertain
- Progressive Enrichment: Build agreement incrementally
- Zero 422 Errors: All validation is lenient with fallbacks
"""

import json
import logging
import re
import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from app.core.config import settings
from app.core.llm_client import get_chat_model
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#                              CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

class Config:
    """Pipeline configuration."""
    # Models
    FAST_MODEL = "gpt-4o-mini"  # Quick extractions
    POWER_MODEL = "gpt-4o"      # Complex reasoning
    
    # Chunking
    MAX_CHUNK_CHARS = 25000     # ~6K tokens per chunk
    MIN_CHUNK_CHARS = 1000
    MAX_PARALLEL_CALLS = 3     # Avoid rate limits
    
    # Timeouts
    API_TIMEOUT = 90
    MAX_RETRIES = 2


# ═══════════════════════════════════════════════════════════════════════════════
#                              DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExtractedParty:
    name: str
    role: str  # Borrower, Lender, Administrative Agent, etc.
    lei: Optional[str] = None
    address: Optional[str] = None
    confidence: float = 1.0
    source_section: Optional[str] = None


@dataclass
class ExtractedFacility:
    name: str
    amount: Optional[float] = None
    currency: str = "USD"
    facility_type: Optional[str] = None  # Term, Revolving, LOC
    spread_bps: Optional[float] = None
    benchmark: Optional[str] = None  # SOFR, LIBOR
    maturity_date: Optional[str] = None
    confidence: float = 1.0
    source_section: Optional[str] = None


@dataclass
class ExtractedAgreement:
    """Incrementally built agreement structure."""
    agreement_date: Optional[str] = None
    effective_date: Optional[str] = None
    governing_law: Optional[str] = None
    parties: List[ExtractedParty] = field(default_factory=list)
    facilities: List[ExtractedFacility] = field(default_factory=list)
    total_commitment: Optional[float] = None
    currency: str = "USD"
    sustainability_linked: bool = False
    esg_terms: List[str] = field(default_factory=list)
    
    # Metadata
    extraction_stages_completed: List[str] = field(default_factory=list)
    confidence_score: float = 0.0
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "agreement_date": self.agreement_date,
            "effective_date": self.effective_date,
            "governing_law": self.governing_law,
            "parties": [
                {"name": p.name, "role": p.role, "lei": p.lei, "confidence": p.confidence}
                for p in self.parties
            ],
            "facilities": [
                {
                    "name": f.name, 
                    "amount": f.amount, 
                    "currency": f.currency,
                    "facility_type": f.facility_type,
                    "spread_bps": f.spread_bps,
                    "benchmark": f.benchmark,
                    "maturity_date": f.maturity_date,
                    "confidence": f.confidence
                }
                for f in self.facilities
            ],
            "total_commitment": self.total_commitment,
            "sustainability_linked": self.sustainability_linked,
            "esg_terms": self.esg_terms,
            "confidence_score": self.confidence_score,
            "warnings": self.warnings,
            "extraction_stages": self.extraction_stages_completed
        }


@dataclass
class DocumentSection:
    """A semantic section of the document."""
    title: str
    content: str
    section_type: str  # article, exhibit, schedule, preamble, signature
    start_char: int
    end_char: int
    importance: float = 0.5  # 0-1 scale


# ═══════════════════════════════════════════════════════════════════════════════
#                           STAGE 1: DOCUMENT STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════

class DocumentStructureAnalyzer:
    """Intelligent document structure analysis."""
    
    # Pattern library for credit agreement structures
    PATTERNS = {
        "article": re.compile(
            r'ARTICLE\s+([IVX]+|\d+)[:\s]+([A-Z][A-Z\s,]+?)(?:\n|$)',
            re.IGNORECASE | re.MULTILINE
        ),
        "section": re.compile(
            r'(?:^|\n)(\d+\.\d+)\s+([A-Z][^.\n]{5,60})',
            re.MULTILINE
        ),
        "exhibit": re.compile(
            r'EXHIBIT\s+([A-Z0-9-]+)[:\s]*([A-Z][A-Z\s,]*)?',
            re.IGNORECASE
        ),
        "schedule": re.compile(
            r'SCHEDULE\s+([A-Z0-9.-]+)[:\s]*([A-Z][A-Z\s,]*)?',
            re.IGNORECASE
        ),
    }
    
    # High-value sections for extraction
    HIGH_VALUE_KEYWORDS = {
        "parties": ["party", "parties", "borrower", "lender", "agent", "guarantor"],
        "facilities": ["credit", "facility", "commitment", "loan", "term loan", "revolver"],
        "terms": ["interest", "rate", "spread", "basis point", "sofr", "libor", "margin"],
        "dates": ["maturity", "termination", "effective", "closing", "amendment"],
        "esg": ["sustainability", "environmental", "esg", "green", "social", "kpi"],
    }
    
    def analyze(self, text: str) -> List[DocumentSection]:
        """Analyze document structure and return semantic sections."""
        sections = []
        
        # 1. Extract preamble (first part before Article I)
        first_article = self.PATTERNS["article"].search(text)
        if first_article:
            preamble = text[:first_article.start()]
            if len(preamble) > Config.MIN_CHUNK_CHARS:
                sections.append(DocumentSection(
                    title="Preamble",
                    content=preamble[:Config.MAX_CHUNK_CHARS],
                    section_type="preamble",
                    start_char=0,
                    end_char=first_article.start(),
                    importance=0.95  # Critical for parties & dates
                ))
        
        # 2. Extract Articles
        article_matches = list(self.PATTERNS["article"].finditer(text))
        for i, match in enumerate(article_matches):
            start = match.start()
            end = article_matches[i + 1].start() if i + 1 < len(article_matches) else len(text)
            
            title = f"Article {match.group(1)}: {match.group(2).strip()}"
            content = text[start:end]
            
            # Score importance based on keywords
            importance = self._score_importance(title, content)
            
            sections.append(DocumentSection(
                title=title,
                content=content[:Config.MAX_CHUNK_CHARS],
                section_type="article",
                start_char=start,
                end_char=end,
                importance=importance
            ))
        
        # 3. Extract Exhibits and Schedules (often have commitment tables)
        for match in self.PATTERNS["exhibit"].finditer(text):
            exhibit_start = match.start()
            # Find end (next exhibit/schedule or end of doc)
            next_exhibit = self.PATTERNS["exhibit"].search(text, exhibit_start + 1)
            exhibit_end = next_exhibit.start() if next_exhibit else min(exhibit_start + 50000, len(text))
            
            content = text[exhibit_start:exhibit_end]
            sections.append(DocumentSection(
                title=f"Exhibit {match.group(1)}",
                content=content[:Config.MAX_CHUNK_CHARS],
                section_type="exhibit",
                start_char=exhibit_start,
                end_char=exhibit_end,
                importance=0.7
            ))
        
        for match in self.PATTERNS["schedule"].finditer(text):
            schedule_start = match.start()
            next_schedule = self.PATTERNS["schedule"].search(text, schedule_start + 1)
            schedule_end = next_schedule.start() if next_schedule else min(schedule_start + 50000, len(text))
            
            content = text[schedule_start:schedule_end]
            
            # Schedules with commitments are high value
            importance = 0.9 if "commitment" in content.lower() else 0.6
            
            sections.append(DocumentSection(
                title=f"Schedule {match.group(1)}",
                content=content[:Config.MAX_CHUNK_CHARS],
                section_type="schedule",
                start_char=schedule_start,
                end_char=schedule_end,
                importance=importance
            ))
        
        # 4. Signature pages (last 20K chars often have dates)
        if len(text) > 30000:
            sections.append(DocumentSection(
                title="Signature Pages",
                content=text[-20000:],
                section_type="signature",
                start_char=len(text) - 20000,
                end_char=len(text),
                importance=0.8
            ))
        
        # Sort by importance and limit
        sections.sort(key=lambda s: s.importance, reverse=True)
        
        logger.info(f"Identified {len(sections)} document sections")
        for s in sections[:5]:
            logger.info(f"  [{s.importance:.2f}] {s.title[:50]}")
        
        return sections
    
    def _score_importance(self, title: str, content: str) -> float:
        """Score section importance based on keywords."""
        combined = (title + " " + content[:2000]).lower()
        score = 0.5
        
        for category, keywords in self.HIGH_VALUE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in combined:
                    score += 0.1
                    break  # One match per category
        
        return min(score, 1.0)


# ═══════════════════════════════════════════════════════════════════════════════
#                        STAGE 2: ENTITY-FOCUSED EXTRACTION
# ═══════════════════════════════════════════════════════════════════════════════

class EntityExtractor:
    """Specialized extractors for each entity type."""
    
    def __init__(self):
        # Use LLM client abstraction instead of direct OpenAI client
        self.llm = get_chat_model(temperature=0)
    
    def _call_llm(self, prompt: str, content: str, model: str = None) -> Dict[str, Any]:
        """Make LLM call with robust error handling using LangChain.
        
        Note: model parameter is kept for compatibility but LLM provider/model
        is configured via environment variables (LLM_PROVIDER, LLM_MODEL).
        """
        for attempt in range(Config.MAX_RETRIES + 1):
            try:
                # Use LangChain message format
                messages = [
                    SystemMessage(content=prompt),
                    HumanMessage(content=content)
                ]
                
                # Invoke LLM
                response = self.llm.invoke(messages)
                
                # Extract content from LangChain response
                response_text = response.content if hasattr(response, 'content') else str(response)
                
                return json.loads(response_text)
            except json.JSONDecodeError:
                logger.warning(f"JSON parse error on attempt {attempt + 1}")
                continue
            except Exception as e:
                logger.warning(f"LLM call failed attempt {attempt + 1}: {e}")
                if attempt == Config.MAX_RETRIES:
                    return {"error": str(e)}
        
        return {"error": "Max retries exceeded"}
    
    def extract_parties(self, sections: List[DocumentSection]) -> List[ExtractedParty]:
        """Extract all parties from relevant sections."""
        prompt = """Extract ALL parties from this credit agreement section.

Return JSON:
{
  "parties": [
    {
      "name": "Full Legal Name Inc.",
      "role": "Borrower/Lender/Administrative Agent/Collateral Agent/Guarantor/Issuing Bank/Swingline Lender",
      "lei": "20-character LEI or null",
      "jurisdiction": "state/country of organization or null"
    }
  ]
}

RULES:
- Include ALL parties mentioned (there can be 50+ lenders)
- Use exact legal names from the document
- Common roles: Borrower, Parent Borrower, Subsidiary Borrower, Administrative Agent, Collateral Agent, Lender, Issuing Bank
- LEI is a 20-character alphanumeric code"""

        all_parties = []
        
        # Focus on high-importance sections for parties
        party_sections = [s for s in sections if s.importance > 0.7 or s.section_type == "preamble"]
        
        for section in party_sections[:5]:  # Limit API calls
            result = self._call_llm(prompt, section.content[:15000])
            
            if "parties" in result:
                for p in result["parties"]:
                    all_parties.append(ExtractedParty(
                        name=p.get("name", "Unknown"),
                        role=p.get("role", "Unknown"),
                        lei=p.get("lei"),
                        source_section=section.title
                    ))
        
        # Dedupe by name
        seen = set()
        unique = []
        for p in all_parties:
            key = p.name.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        logger.info(f"Extracted {len(unique)} unique parties")
        return unique
    
    def extract_facilities(self, sections: List[DocumentSection]) -> List[ExtractedFacility]:
        """Extract all loan facilities."""
        prompt = """Extract ALL loan facilities from this credit agreement section.

Return JSON:
{
  "facilities": [
    {
      "name": "Term Loan A/Term Loan B/Revolving Credit Facility/Letter of Credit Subfacility/Swingline Subfacility",
      "amount": 1000000000,
      "currency": "USD",
      "type": "Term/Revolving/LOC/Swingline",
      "spread_bps": 250,
      "benchmark": "SOFR/Term SOFR/LIBOR/Prime/Base Rate",
      "maturity_date": "YYYY-MM-DD or null"
    }
  ],
  "total_commitment": 5000000000
}

RULES:
- Include ALL facilities (Term Loans, Revolvers, Subfacilities, etc.)
- Amounts as pure numbers (no commas): 1000000000 not 1,000,000,000
- Spread in basis points: 2.50% = 250 bps
- Look for Commitment Schedules which list all lender commitments"""

        all_facilities = []
        total_commitment = None
        
        # Focus on credit articles and schedules
        facility_sections = [s for s in sections 
                           if "credit" in s.title.lower() 
                           or "commitment" in s.title.lower()
                           or "schedule" in s.section_type
                           or s.importance > 0.8]
        
        for section in facility_sections[:6]:
            result = self._call_llm(prompt, section.content[:20000])
            
            if "facilities" in result:
                for f in result["facilities"]:
                    all_facilities.append(ExtractedFacility(
                        name=f.get("name", "Unknown Facility"),
                        amount=self._parse_amount(f.get("amount")),
                        currency=f.get("currency", "USD"),
                        facility_type=f.get("type"),
                        spread_bps=f.get("spread_bps"),
                        benchmark=f.get("benchmark"),
                        maturity_date=f.get("maturity_date"),
                        source_section=section.title
                    ))
            
            if "total_commitment" in result and result["total_commitment"]:
                total_commitment = self._parse_amount(result["total_commitment"])
        
        # Dedupe by name and merge
        merged = self._merge_facilities(all_facilities)
        
        logger.info(f"Extracted {len(merged)} unique facilities, total: ${total_commitment:,.0f}" if total_commitment else f"Extracted {len(merged)} facilities")
        return merged, total_commitment
    
    def extract_dates_and_terms(self, sections: List[DocumentSection]) -> Dict[str, Any]:
        """Extract key dates and interest terms."""
        prompt = """Extract key dates and terms from this credit agreement section.

Return JSON:
{
  "agreement_date": "YYYY-MM-DD",
  "effective_date": "YYYY-MM-DD or null",
  "maturity_date": "YYYY-MM-DD",
  "governing_law": "New York/Delaware/English/etc",
  "interest_terms": {
    "benchmark": "Term SOFR/Daily Simple SOFR/LIBOR",
    "spread_range_bps": {"min": 150, "max": 300},
    "default_rate_additional_bps": 200
  },
  "sustainability_linked": true/false,
  "esg_kpis": ["description of any ESG KPIs"]
}"""

        for section in sections[:3]:  # Preamble and first articles
            result = self._call_llm(prompt, section.content[:15000])
            if "agreement_date" in result or "governing_law" in result:
                return result
        
        return {}
    
    def _parse_amount(self, value) -> Optional[float]:
        """Parse monetary amount from various formats."""
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove $, commas, spaces
            cleaned = re.sub(r'[$,\s]', '', value)
            try:
                return float(cleaned)
            except:
                return None
        return None
    
    def _merge_facilities(self, facilities: List[ExtractedFacility]) -> List[ExtractedFacility]:
        """Merge duplicate facilities, keeping best data."""
        by_name = {}
        for f in facilities:
            key = f.name.lower().strip()
            if key not in by_name:
                by_name[key] = f
            else:
                # Merge: prefer non-null values
                existing = by_name[key]
                if f.amount and not existing.amount:
                    existing.amount = f.amount
                if f.spread_bps and not existing.spread_bps:
                    existing.spread_bps = f.spread_bps
                if f.maturity_date and not existing.maturity_date:
                    existing.maturity_date = f.maturity_date
        
        return list(by_name.values())


# ═══════════════════════════════════════════════════════════════════════════════
#                        STAGE 3: RECONCILIATION & VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

class Reconciler:
    """Cross-reference and validate extracted data."""
    
    def reconcile(self, agreement: ExtractedAgreement) -> ExtractedAgreement:
        """Validate and reconcile extracted data."""
        warnings = []
        
        # Check: At least one borrower
        borrowers = [p for p in agreement.parties if "borrower" in p.role.lower()]
        if not borrowers:
            warnings.append("No Borrower party identified")
            agreement.confidence_score -= 0.2
        
        # Check: At least one facility
        if not agreement.facilities:
            warnings.append("No facilities extracted")
            agreement.confidence_score -= 0.3
        
        # Check: Total commitment matches sum of facilities
        if agreement.facilities and agreement.total_commitment:
            facility_sum = sum(f.amount or 0 for f in agreement.facilities)
            if facility_sum > 0:
                diff_pct = abs(facility_sum - agreement.total_commitment) / agreement.total_commitment
                if diff_pct > 0.1:  # More than 10% difference
                    warnings.append(f"Facility sum (${facility_sum:,.0f}) differs from total commitment (${agreement.total_commitment:,.0f})")
        
        # Check: Agreement date is valid
        if agreement.agreement_date:
            try:
                date = datetime.strptime(agreement.agreement_date, "%Y-%m-%d")
                if date.year < 2000 or date.year > 2030:
                    warnings.append(f"Unusual agreement date: {agreement.agreement_date}")
            except:
                warnings.append(f"Invalid date format: {agreement.agreement_date}")
        
        # Calculate confidence
        confidence = 1.0
        if not borrowers:
            confidence -= 0.2
        if not agreement.facilities:
            confidence -= 0.2
        if not agreement.agreement_date:
            confidence -= 0.1
        if not agreement.governing_law:
            confidence -= 0.1
        
        agreement.confidence_score = max(0, min(1, confidence))
        agreement.warnings = warnings
        
        return agreement


# ═══════════════════════════════════════════════════════════════════════════════
#                        STAGE 4: SELF-HEALING ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════════════

class Enricher:
    """Fill gaps with targeted queries."""
    
    def __init__(self):
        # Use LLM client abstraction instead of direct OpenAI client
        self.llm = get_chat_model(temperature=0)
        self.extractor = EntityExtractor()
    
    def enrich(self, agreement: ExtractedAgreement, text: str) -> ExtractedAgreement:
        """Attempt to fill missing critical fields."""
        
        # If no borrower, try targeted search
        if not any("borrower" in p.role.lower() for p in agreement.parties):
            logger.info("Enrichment: Searching for Borrower...")
            borrower = self._find_borrower(text)
            if borrower:
                agreement.parties.insert(0, borrower)
        
        # If no facilities, try commitment schedule
        if not agreement.facilities:
            logger.info("Enrichment: Searching for facilities in schedules...")
            facilities = self._find_facilities_in_schedules(text)
            agreement.facilities.extend(facilities)
        
        # If no dates, try signature pages
        if not agreement.agreement_date:
            logger.info("Enrichment: Searching for dates...")
            date = self._find_agreement_date(text)
            if date:
                agreement.agreement_date = date
        
        return agreement
    
    def _find_borrower(self, text: str) -> Optional[ExtractedParty]:
        """Targeted search for Borrower party."""
        # Look for common patterns
        patterns = [
            r'(?:the\s+)?["\']?([A-Z][A-Za-z\s,\.]+(?:Inc|LLC|Corp|LP|Ltd)\.?)["\']?\s*(?:,\s*)?(?:a[s]?\s+)?(?:the\s+)?["\']?Borrower["\']?',
            r'Borrower["\']?\s*(?:means\s+)?["\']?([A-Z][A-Za-z\s,\.]+(?:Inc|LLC|Corp|LP|Ltd)\.?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:50000], re.IGNORECASE)
            if match:
                return ExtractedParty(
                    name=match.group(1).strip(),
                    role="Borrower",
                    confidence=0.9,
                    source_section="Pattern Match"
                )
        
        return None
    
    def _find_facilities_in_schedules(self, text: str) -> List[ExtractedFacility]:
        """Search commitment schedules for facility data."""
        # Look for dollar amounts with context
        facilities = []
        
        # Pattern for commitment amounts
        amount_pattern = r'\$\s*([\d,]+(?:\.\d{2})?)\s*(?:million|MM|M)?'
        
        for match in re.finditer(amount_pattern, text):
            amount_str = match.group(1).replace(',', '')
            amount = float(amount_str)
            
            # Check context for facility type
            context = text[max(0, match.start()-200):match.end()+100].lower()
            
            if "term loan" in context or "term facility" in context:
                facilities.append(ExtractedFacility(
                    name="Term Loan",
                    amount=amount * (1_000_000 if amount < 10000 else 1),
                    confidence=0.7,
                    source_section="Schedule Pattern"
                ))
            elif "revolv" in context:
                facilities.append(ExtractedFacility(
                    name="Revolving Credit Facility",
                    amount=amount * (1_000_000 if amount < 10000 else 1),
                    confidence=0.7,
                    source_section="Schedule Pattern"
                ))
        
        return facilities[:5]  # Limit to avoid noise
    
    def _find_agreement_date(self, text: str) -> Optional[str]:
        """Search for agreement date."""
        # Look for "dated as of" patterns
        patterns = [
            r'dated\s+(?:as\s+of\s+)?([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
            r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?[A-Z][a-z]+,?\s+\d{4})',
            r'effective\s+(?:as\s+of\s+)?([A-Z][a-z]+\s+\d{1,2},?\s+\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text[:30000], re.IGNORECASE)
            if match:
                date_str = match.group(1)
                # Try to parse and normalize
                for fmt in ["%B %d, %Y", "%B %d %Y", "%d %B %Y", "%d %B, %Y"]:
                    try:
                        dt = datetime.strptime(date_str.replace(",", "").strip(), fmt)
                        return dt.strftime("%Y-%m-%d")
                    except:
                        continue
        
        return None


# ═══════════════════════════════════════════════════════════════════════════════
#                              MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

class AgenticExtractionPipeline:
    """
    The Revolutionary Agentic Document Understanding Pipeline.
    
    Handles 190+ page credit agreements with:
    - Multi-stage processing
    - Entity-focused extraction
    - Self-healing enrichment
    - Guaranteed no 422 errors
    """
    
    def __init__(self):
        self.structure_analyzer = DocumentStructureAnalyzer()
        self.entity_extractor = EntityExtractor()
        self.reconciler = Reconciler()
        self.enricher = Enricher()
    
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Main extraction pipeline.
        
        Args:
            text: Full credit agreement text (can be 500K+ chars)
            
        Returns:
            Dict with status, agreement data, and metadata
        """
        try:
            logger.info(f"═══ AGENTIC PIPELINE START ═══ ({len(text):,} chars)")
            start_time = datetime.now()
            
            agreement = ExtractedAgreement()
            
            # ─────────────────────────────────────────────────────────────
            # STAGE 1: Document Structure Analysis
            # ─────────────────────────────────────────────────────────────
            logger.info("Stage 1: Analyzing document structure...")
            sections = self.structure_analyzer.analyze(text)
            agreement.extraction_stages_completed.append("structure_analysis")
            
            if not sections:
                # Fallback: treat as single chunk
                sections = [DocumentSection(
                    title="Full Document",
                    content=text[:Config.MAX_CHUNK_CHARS],
                    section_type="unknown",
                    start_char=0,
                    end_char=len(text),
                    importance=1.0
                )]
            
            # ─────────────────────────────────────────────────────────────
            # STAGE 2: Entity-Focused Extraction (Parallel)
            # ─────────────────────────────────────────────────────────────
            logger.info("Stage 2: Entity-focused extraction...")
            
            with ThreadPoolExecutor(max_workers=Config.MAX_PARALLEL_CALLS) as executor:
                # Submit parallel tasks
                parties_future = executor.submit(self.entity_extractor.extract_parties, sections)
                facilities_future = executor.submit(self.entity_extractor.extract_facilities, sections)
                terms_future = executor.submit(self.entity_extractor.extract_dates_and_terms, sections)
                
                # Collect results
                agreement.parties = parties_future.result()
                facilities_result = facilities_future.result()
                agreement.facilities = facilities_result[0] if isinstance(facilities_result, tuple) else facilities_result
                agreement.total_commitment = facilities_result[1] if isinstance(facilities_result, tuple) and len(facilities_result) > 1 else None
                
                terms = terms_future.result()
                agreement.agreement_date = terms.get("agreement_date")
                agreement.effective_date = terms.get("effective_date")
                agreement.governing_law = terms.get("governing_law")
                agreement.sustainability_linked = terms.get("sustainability_linked", False)
                agreement.esg_terms = terms.get("esg_kpis", [])
            
            agreement.extraction_stages_completed.append("entity_extraction")
            
            # ─────────────────────────────────────────────────────────────
            # STAGE 3: Reconciliation & Validation
            # ─────────────────────────────────────────────────────────────
            logger.info("Stage 3: Reconciliation...")
            agreement = self.reconciler.reconcile(agreement)
            agreement.extraction_stages_completed.append("reconciliation")
            
            # ─────────────────────────────────────────────────────────────
            # STAGE 4: Self-Healing Enrichment (if needed)
            # ─────────────────────────────────────────────────────────────
            if agreement.confidence_score < 0.7:
                logger.info("Stage 4: Enrichment (low confidence)...")
                agreement = self.enricher.enrich(agreement, text)
                agreement.extraction_stages_completed.append("enrichment")
            
            # ─────────────────────────────────────────────────────────────
            # Final Result
            # ─────────────────────────────────────────────────────────────
            elapsed = (datetime.now() - start_time).total_seconds()
            
            status = "success"
            if agreement.confidence_score < 0.5:
                status = "partial"
            if not agreement.parties and not agreement.facilities:
                status = "failed"
            
            logger.info(f"═══ PIPELINE COMPLETE ═══ ({elapsed:.1f}s, confidence: {agreement.confidence_score:.0%})")
            
            return {
                "status": status,
                "agreement": agreement.to_dict(),
                "message": f"Extracted {len(agreement.parties)} parties, {len(agreement.facilities)} facilities in {elapsed:.1f}s",
                "metadata": {
                    "document_chars": len(text),
                    "sections_analyzed": len(sections),
                    "stages_completed": agreement.extraction_stages_completed,
                    "processing_time_seconds": elapsed
                }
            }
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            return {
                "status": "error",
                "agreement": None,
                "message": f"Extraction failed: {str(e)[:300]}",
                "metadata": {"error": str(e)}
            }


# ═══════════════════════════════════════════════════════════════════════════════
#                              PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def extract_with_agentic_pipeline(text: str) -> Dict[str, Any]:
    """
    Extract credit agreement data using the revolutionary agentic pipeline.
    
    This is the main entry point for the extraction system.
    """
    pipeline = AgenticExtractionPipeline()
    return pipeline.extract(text)
