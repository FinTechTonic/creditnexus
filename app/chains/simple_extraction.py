"""Ultra-simple extraction using raw OpenAI API with JSON mode.

No Pydantic validation during extraction = no 422 errors.
Validation happens AFTER we have the data, with lenient fallbacks.
"""

import json
import logging
import re
from typing import Optional, Dict, Any
from openai import OpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_client() -> OpenAI:
    """Create OpenAI client."""
    return OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())


def extract_key_sections(text: str, max_chars: int = 80000) -> str:
    """Extract the most important sections from a credit agreement."""
    if len(text) <= max_chars:
        return text
    
    logger.info(f"Summarizing document from {len(text)} to ~{max_chars} chars...")
    
    # Take strategic sections
    sections = []
    
    # First 25K chars (preamble, parties)
    sections.append(text[:25000])
    
    # Search for key patterns in the rest
    rest = text[25000:]
    
    patterns = [
        (r'ARTICLE\s+II[^A]+', 10000),   # Credits/Facilities
        (r'commitment[^.]+\$[0-9,]+[^.]+\.', 5000),  # Commitment amounts
        (r'interest\s+rate[^.]+\.', 3000),  # Interest rates
        (r'maturity[^.]+\d{4}[^.]+\.', 2000),  # Maturity dates
        (r'SOFR|LIBOR|benchmark[^.]+\.', 2000),  # Rate benchmarks
    ]
    
    for pattern, max_len in patterns:
        matches = re.findall(pattern, rest, re.IGNORECASE | re.DOTALL)
        for match in matches[:2]:
            if len(match) > 100:
                sections.append(match[:max_len])
    
    # Last 10K chars (signatures, governing law)
    sections.append(text[-10000:])
    
    result = "\n\n---\n\n".join(sections)
    logger.info(f"Reduced to {len(result)} chars")
    return result[:max_chars]


def extract_simple(text: str) -> Dict[str, Any]:
    """
    Simple, bulletproof extraction using raw OpenAI API.
    
    Returns a plain dict - no Pydantic validation.
    """
    client = create_client()
    
    # Summarize long documents
    doc_text = extract_key_sections(text, max_chars=60000)
    
    prompt = """Extract credit agreement data as JSON. Use null for missing fields.

Required format:
{
  "status": "success" or "partial" or "not_a_credit_agreement",
  "agreement_date": "YYYY-MM-DD or null",
  "governing_law": "state/country or null",
  "parties": [
    {"name": "...", "role": "Borrower/Lender/Agent", "lei": "... or null"}
  ],
  "facilities": [
    {
      "name": "Term Loan/Revolver/etc",
      "amount": 1000000,
      "currency": "USD",
      "spread_bps": 250,
      "benchmark": "SOFR/LIBOR/etc or null",
      "maturity": "YYYY-MM-DD or null"
    }
  ],
  "total_commitment": 1000000,
  "sustainability_linked": true/false,
  "message": "any notes about extraction"
}

RULES:
- amounts as pure numbers (no commas): 1000000 not 1,000,000
- spread in basis points: 2.5% = 250 bps
- at least one party with role "Borrower" 
- at least one facility"""

    logger.info(f"Calling OpenAI with {len(doc_text)} chars...")
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Document:\n{doc_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=4000,
            timeout=120
        )
        
        content = response.choices[0].message.content
        logger.info(f"Got response: {len(content)} chars")
        
        # Parse JSON
        data = json.loads(content)
        
        # Ensure required fields exist
        data.setdefault("status", "success")
        data.setdefault("parties", [])
        data.setdefault("facilities", [])
        data.setdefault("message", None)
        
        logger.info(f"Extracted: {len(data.get('parties', []))} parties, {len(data.get('facilities', []))} facilities")
        
        return {
            "status": data.get("status", "success"),
            "agreement": {
                "agreement_date": data.get("agreement_date"),
                "governing_law": data.get("governing_law"),
                "parties": data.get("parties", []),
                "facilities": data.get("facilities", []),
                "total_commitment": data.get("total_commitment"),
                "sustainability_linked": data.get("sustainability_linked", False),
            },
            "message": data.get("message")
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"JSON parse error: {e}")
        return {
            "status": "error",
            "agreement": None,
            "message": f"Failed to parse extraction result: {str(e)}"
        }
    except Exception as e:
        logger.error(f"Extraction error: {e}")
        return {
            "status": "error", 
            "agreement": None,
            "message": f"Extraction failed: {str(e)}"
        }


def extract_credit_agreement_simple(text: str) -> Dict[str, Any]:
    """Main entry point for simple extraction."""
    logger.info(f"Starting simple extraction for {len(text)} chars")
    return extract_simple(text)
