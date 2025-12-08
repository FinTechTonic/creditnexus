"""Demonstration script for processing long credit agreement documents.

This script demonstrates the Map-Reduce extraction strategy for handling
documents that exceed token limits or are too long for single-pass extraction.
"""

import logging
from app.chains.extraction_chain import extract_data_smart
from app.utils.pdf_extractor import extract_text_from_pdf
from app.models.cdm import CreditAgreement, ExtractionResult, ExtractionStatus

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Sample long credit agreement text with multiple Articles
LONG_AGREEMENT_TEXT = """
CREDIT AGREEMENT

Dated as of October 15, 2023

This CREDIT AGREEMENT, dated as of October 15, 2023, is entered into by and among 
ACME INDUSTRIES INC., a Delaware corporation (the "Borrower"), GLOBAL BANK CORP., 
as Administrative Agent and Lender, and the other Lenders party hereto.

ARTICLE I: DEFINITIONS

1.01 Defined Terms. As used in this Agreement, the following terms shall have the meanings set forth below:

"Administrative Agent" means Global Bank Corp., in its capacity as administrative agent for the Lenders.

"Borrower" means ACME INDUSTRIES INC., a Delaware corporation.

"Credit Agreement" means this Credit Agreement, as it may be amended, restated, or modified from time to time.

"Term Loan Facility" means the term loan facility established pursuant to Article II hereof.

ARTICLE II: THE CREDITS

2.01 Term Loan Facility. The Lenders agree to provide a Term Loan Facility in the aggregate principal amount of $500,000,000 USD.

2.02 Interest Rates. The loans shall bear interest at a rate per annum equal to Term SOFR plus a margin of 2.75%. Interest payments shall be made quarterly, on the last day of each calendar quarter.

2.03 Maturity. The Maturity Date shall be October 15, 2028.

ARTICLE III: REPRESENTATIONS AND WARRANTIES

3.01 Organization. The Borrower is a corporation duly organized, validly existing and in good standing under the laws of the State of Delaware.

3.02 Authority. The Borrower has the corporate power and authority to execute, deliver and perform this Agreement.

ARTICLE IV: CONDITIONS PRECEDENT

4.01 Conditions to Initial Credit Extension. The obligation of each Lender to make its initial Credit Extension is subject to satisfaction of the conditions set forth in this Article IV.

ARTICLE V: COVENANTS

5.01 Affirmative Covenants. The Borrower agrees that, so long as any Lender has any Commitment hereunder or any Loan remains unpaid, the Borrower will perform the obligations set forth in this Section 5.01.

ARTICLE VI: EVENTS OF DEFAULT

6.01 Events of Default. Each of the following shall constitute an Event of Default under this Agreement.

ARTICLE VII: MISCELLANEOUS

7.01 Governing Law. This agreement is governed by the laws of the State of New York.

7.02 Jurisdiction. Any legal action or proceeding arising under this Agreement shall be brought in the courts of the State of New York.
"""


def main():
    """Demonstrate long document processing with Map-Reduce."""
    print("=" * 70)
    print("CreditNexus: Long Document Processing Demo (Map-Reduce)")
    print("=" * 70)
    print()
    
    # Option 1: Process from text
    print("Processing long credit agreement text...")
    print(f"Document length: {len(LONG_AGREEMENT_TEXT)} characters")
    print()
    
    try:
        result: ExtractionResult = extract_data_smart(LONG_AGREEMENT_TEXT)

        if result.status == ExtractionStatus.FAILURE:
            print("Extraction marked as irrelevant_document/failed.")
            print(result.model_dump_json(indent=2))
            return

        agreement = result.agreement
        if agreement is None:
            raise ValueError("No agreement returned despite non-failure status")
        
        print("Extraction Successful!")
        print()
        print("Extracted Credit Agreement Data:")
        print("-" * 70)
        print(agreement.model_dump_json(indent=2))
        print("-" * 70)
        print()
        
        # Verify key data
        print("Verification:")
        print(f"✓ Agreement Date: {agreement.agreement_date}")
        print(f"✓ Parties: {len(agreement.parties)} found")
        for party in agreement.parties:
            print(f"  - {party.name} ({party.role})")
        print(f"✓ Facilities: {len(agreement.facilities)} found")
        for facility in agreement.facilities:
            print(f"  - {facility.facility_name}: ${facility.commitment_amount.amount:,.0f} {facility.commitment_amount.currency.value}")
        print(f"✓ Governing Law: {agreement.governing_law}")
        print()
        
    except Exception as e:
        print(f"ERROR: {e}")
        logger.exception("Extraction failed")
        return
    
    # Option 2: Process from PDF (if available)
    print("=" * 70)
    print("PDF Processing Example")
    print("=" * 70)
    print()
    print("To process a PDF file, use:")
    print()
    print("  from app.utils.pdf_extractor import extract_text_from_pdf")
    print("  from app.chains.extraction_chain import extract_data_smart")
    print()
    print("  text = extract_text_from_pdf('path/to/agreement.pdf')")
    print("  result = extract_data_smart(text)")
    print()
    print("Note: Install PyPDF2 for PDF support: pip install PyPDF2")
    print()
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

