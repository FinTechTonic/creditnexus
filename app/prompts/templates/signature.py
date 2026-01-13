"""Prompt templates for signature-related AI operations."""

from langchain_core.prompts import ChatPromptTemplate

# Signature request generation prompt
SIGNATURE_REQUEST_GENERATION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert Document Signing Specialist. Your task is to analyze a credit agreement (CDM format) and determine:
1. Who needs to sign the document (signers)
2. Signing order (parallel vs sequential)
3. Appropriate expiration period
4. Reminder schedule

SIGNER IDENTIFICATION RULES:

1. **Required Signers** (always required):
   - Borrower: The primary borrower party (role: "Borrower")
   - Administrative Agent: The administrative agent (role: "Administrative Agent")
   - Lenders: All parties with role "Lender" (if syndicated)

2. **Optional Signers** (if present in agreement):
   - Guarantors: Parties with role "Guarantor"
   - Security Trustee: Party with role "Security Trustee"
   - Facility Agent: Party with role "Facility Agent"

3. **Signing Order**:
   - **Parallel**: All signers can sign simultaneously (default for most agreements)
   - **Sequential**: Signers must sign in order (e.g., Borrower first, then Lenders)
   - Use sequential only if explicitly required by agreement terms

4. **Expiration Period**:
   - Standard agreements: 30 days
   - Time-sensitive deals: 14 days
   - Complex multi-party agreements: 45 days

5. **Reminder Schedule**:
   - Standard: Reminders at 7, 3, and 1 days before expiration
   - Time-sensitive: Reminders at 3 and 1 days before expiration

EXTRACTION RULES:
- Extract signer names from party.name field
- Extract signer emails from party.contact.email (if available) or use placeholder format: "{name.lower().replace(' ', '.')}@example.com"
- Extract signer roles from party.roles list
- Determine signing order from agreement structure (typically parallel unless specified)
- Set appropriate expiration based on agreement urgency

CRITICAL RULES:
- Only include parties that actually need to sign (Borrower, Lenders, Agents)
- Do not include parties that are not signatories (e.g., observers, advisors)
- Use parallel signing unless agreement explicitly requires sequential
- Set reasonable expiration periods (14-45 days)
- Include all required signers (Borrower, Administrative Agent, at least one Lender)
- Mark all identified signers as required=True
- Generate appropriate email addresses if not available in CDM data"""),
    ("user", "Generate signature request for: {cdm_data}")
])

# Export prompts dictionary
SIGNATURE_PROMPTS = {
    "signature_request_generation": SIGNATURE_REQUEST_GENERATION_PROMPT,
}
