"""Demonstration script for the CreditNexus financial AI agent.

This script demonstrates the complete pipeline for extracting structured
FINOS CDM-compliant data from unstructured credit agreement text.

Usage:
    Ensure you have a .env file with OPENAI_API_KEY set, then run:
    python main.py
"""

from app.chains.extraction_chain import extract_data
from app.models.cdm import CreditAgreement, ExtractionResult, ExtractionStatus

# Synthetic credit agreement text for demonstration
SAMPLE_AGREEMENT_TEXT = """
This CREDIT AGREEMENT, dated as of October 15, 2023, is entered into by and among 
ACME INDUSTRIES INC., a Delaware corporation (the "Borrower"), GLOBAL BANK CORP., 
as Administrative Agent and Lender, and the other Lenders party hereto.

The Lenders agree to provide a Term Loan Facility in the aggregate principal amount 
of $500,000,000 USD.

The loans shall bear interest at a rate per annum equal to Term SOFR plus a margin 
of 2.75%. Interest payments shall be made quarterly, on the last day of each calendar 
quarter.

The Maturity Date shall be October 15, 2028.

This agreement is governed by the laws of the State of New York.
"""


def main():
    """Execute the demonstration of the extraction pipeline."""
    print("=" * 70)
    print("CreditNexus: FINOS-Compliant Financial AI Agent - Demo")
    print("=" * 70)
    print()
    print("Extracting data from agreement...")
    print()
    
    try:
        # Extract structured data from the sample text
        result: ExtractionResult = extract_data(SAMPLE_AGREEMENT_TEXT)

        if result.status == ExtractionStatus.FAILURE:
            print("Extraction marked as irrelevant_document/failed.")
            print(result.model_dump_json(indent=2))
            return

        agreement = result.agreement
        if agreement is None:
            raise ValueError("No agreement returned despite non-failure status")
        
        # Display the extracted data as formatted JSON
        print("Extraction Successful!")
        print()
        print("Extracted Credit Agreement Data:")
        print("-" * 70)
        print(agreement.model_dump_json(indent=2))
        print("-" * 70)
        print()
        
        # Verify correctness with assertions
        print("Verifying extracted data...")
        
        # Verify agreement date
        assert agreement.agreement_date.year == 2023
        assert agreement.agreement_date.month == 10
        assert agreement.agreement_date.day == 15
        print("✓ Agreement date verified: 2023-10-15")
        
        # Verify spread normalization (2.75% should be 275.0 basis points)
        assert agreement.facilities and len(agreement.facilities) > 0, "No facilities extracted"
        facility = agreement.facilities[0]
        spread_bps = facility.interest_terms.rate_option.spread_bps
        assert spread_bps == 275.0, f"Expected spread_bps=275.0, got {spread_bps}"
        print(f"✓ Spread normalization verified: {spread_bps} basis points (2.75%)")
        
        # Verify parties were extracted
        assert agreement.parties and len(agreement.parties) > 0, "No parties extracted"
        borrower = next((p for p in agreement.parties if "Borrower" in p.role), None)
        assert borrower is not None, "Borrower party not found"
        print(f"✓ Parties extracted: {len(agreement.parties)} party(ies) found")
        print(f"  - Borrower: {borrower.name} ({borrower.role})")
        
        # Verify facility details
        assert facility.commitment_amount.amount == 500000000
        assert facility.commitment_amount.currency.value == "USD"
        print(f"✓ Facility commitment verified: ${facility.commitment_amount.amount:,.0f} {facility.commitment_amount.currency.value}")
        
        # Verify maturity date
        assert facility.maturity_date.year == 2028
        assert facility.maturity_date.month == 10
        assert facility.maturity_date.day == 15
        print(f"✓ Maturity date verified: {facility.maturity_date}")
        
        # Verify governing law
        assert agreement.governing_law and "New York" in agreement.governing_law
        print(f"✓ Governing law verified: {agreement.governing_law}")
        
        print()
        print("=" * 70)
        print("All validations passed! ✓")
        print("=" * 70)
        
    except Exception as e:
        print()
        print("=" * 70)
        print("ERROR: Extraction or validation failed")
        print("=" * 70)
        print(f"Error details: {e}")
        print()
        print("Troubleshooting:")
        print("1. Ensure your .env file contains a valid OPENAI_API_KEY")
        print("2. Run 'python verify_env.py' to check your environment")
        print("3. Ensure you have installed all dependencies: pip install -r requirements.txt")
        raise


if __name__ == "__main__":
    main()

