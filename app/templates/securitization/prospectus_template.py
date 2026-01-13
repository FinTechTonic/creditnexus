"""
Prospectus Supplement template generator for securitization.

Generates Prospectus Supplement documents from securitization pool CDM data.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app.models.cdm import SecuritizationPool as CDMSecuritizationPool

logger = logging.getLogger(__name__)


def generate_prospectus_template(
    pool_data: Dict[str, Any],
    pool_cdm: Optional[CDMSecuritizationPool] = None
) -> Dict[str, Any]:
    """
    Generate Prospectus Supplement template data from securitization pool.
    
    Args:
        pool_data: Pool data dictionary from database
        pool_cdm: Optional CDM SecuritizationPool model
        
    Returns:
        Dictionary with Prospectus Supplement template fields and content
    """
    pool_name = pool_data.get('pool_name', '')
    pool_id = pool_data.get('pool_id', '')
    pool_type = pool_data.get('pool_type', 'ABS')
    total_value = pool_data.get('total_pool_value', '0')
    currency = pool_data.get('currency', 'USD')
    effective_date = pool_data.get('created_at', datetime.now().isoformat())
    
    # Extract parties
    originator_name = "Originator"
    trustee_name = "Trustee"
    servicer_name = "Servicer"
    
    if pool_cdm:
        if pool_cdm.originator:
            originator_name = pool_cdm.originator.name or originator_name
        if pool_cdm.trustee:
            trustee_name = pool_cdm.trustee.name or trustee_name
        if pool_cdm.servicer:
            servicer_name = pool_cdm.servicer.name or servicer_name
    
    # Extract tranches with detailed information
    tranches = pool_data.get('tranches', [])
    tranche_offerings = []
    for tranche in tranches:
        tranche_offerings.append({
            'name': tranche.get('tranche_name', ''),
            'class': tranche.get('tranche_class', ''),
            'size': str(tranche.get('size', {}).get('amount', 0) if isinstance(tranche.get('size'), dict) else tranche.get('size', 0)),
            'interest_rate': str(tranche.get('interest_rate', 0)),
            'risk_rating': tranche.get('risk_rating', 'NR'),
            'priority': str(tranche.get('payment_priority', 999)),
            'maturity': 'As per underlying assets'  # Could be calculated from assets
        })
    
    # Extract underlying assets
    assets = pool_data.get('assets', [])
    asset_details = []
    for asset in assets:
        asset_details.append({
            'type': asset.get('asset_type', ''),
            'id': asset.get('asset_id', ''),
            'value': str(asset.get('asset_value', 0)),
            'currency': asset.get('currency', currency)
        })
    
    # Calculate pool statistics
    total_tranche_value = sum(
        float(t.get('size', {}).get('amount', 0) if isinstance(t.get('size'), dict) else t.get('size', 0))
        for t in tranches
    )
    
    # Generate Prospectus Supplement content
    prospectus_content = {
        'title': f'Prospectus Supplement - {pool_name}',
        'pool_name': pool_name,
        'pool_id': pool_id,
        'pool_type': pool_type,
        'effective_date': effective_date,
        'total_pool_value': str(total_value),
        'total_tranche_value': str(total_tranche_value),
        'currency': currency,
        'originator_name': originator_name,
        'trustee_name': trustee_name,
        'servicer_name': servicer_name,
        'tranches': tranche_offerings,
        'underlying_assets': asset_details,
        'tranche_count': len(tranches),
        'asset_count': len(assets),
    }
    
    # Generate full document text
    prospectus_text = _generate_prospectus_document_text(prospectus_content)
    prospectus_content['document_text'] = prospectus_text
    
    logger.info(f"Generated Prospectus Supplement template for pool {pool_id}")
    return prospectus_content


def _generate_prospectus_document_text(content: Dict[str, Any]) -> str:
    """Generate full Prospectus Supplement document text."""
    
    text = f"""
PROSPECTUS SUPPLEMENT

{content['title']}

Filed Pursuant to Rule 424(b)(5)
Registration Statement No. [TO BE FILED]

{content['effective_date']}

OFFERING SUMMARY

This Prospectus Supplement relates to the offering of {content['tranche_count']} tranche(s) of 
{content['pool_type']} securities (the "Securities") backed by a pool of underlying assets 
with an aggregate value of {content['currency']} {content['total_pool_value']}.

1. THE OFFERING

1.1 Securities Offered
    The offering consists of the following tranches:
"""
    
    for i, tranche in enumerate(content['tranches'], 1):
        text += f"""
    Tranche {i}: {tranche['name']}
        - Class: {tranche['class']}
        - Principal Amount: {content['currency']} {tranche['size']}
        - Interest Rate: {tranche['interest_rate']}% per annum
        - Credit Rating: {tranche['risk_rating']}
        - Payment Priority: {tranche['priority']}
        - Maturity: {tranche['maturity']}
"""
    
    text += f"""
1.2 Total Offering Size
    Total principal amount of Securities offered: {content['currency']} {content['total_tranche_value']}

2. THE POOL

2.1 Pool Characteristics
    Pool Name: {content['pool_name']}
    Pool Type: {content['pool_type']}
    Total Pool Value: {content['currency']} {content['total_pool_value']}
    Number of Underlying Assets: {content['asset_count']}

2.2 Underlying Assets
    The pool is backed by the following underlying assets:
"""
    
    for i, asset in enumerate(content['underlying_assets'], 1):
        text += f"""
    Asset {i}:
        - Type: {asset['type']}
        - Identifier: {asset['id']}
        - Value: {asset['currency']} {asset['value']}
"""
    
    text += f"""
3. PARTIES

3.1 Originator
    {content['originator_name']} (the "Originator") is the originator of the underlying assets.

3.2 Trustee
    {content['trustee_name']} (the "Trustee") will serve as trustee for the securitization trust.

3.3 Servicer
    {content['servicer_name']} (the "Servicer") will service the underlying assets and
    distribute payments to Security holders.

4. RISK FACTORS

    Prospective investors should carefully consider the following risk factors:
    - Credit risk associated with underlying assets
    - Interest rate risk
    - Prepayment risk
    - Liquidity risk
    - Regulatory and legal risks

5. USE OF PROCEEDS

    The net proceeds from the sale of the Securities will be used to:
    - Purchase the underlying assets from the Originator
    - Pay transaction costs and expenses
    - Establish reserves as required

6. DISTRIBUTION

    The Securities will be offered through [TO BE DETERMINED] and may be sold
    to institutional and retail investors.

7. LEGAL MATTERS

    Legal matters relating to the Securities will be passed upon by
    [LEGAL COUNSEL TO BE NAMED].

8. EXPERTS

    The financial statements and other financial information included in this
    Prospectus Supplement have been audited by [AUDITOR TO BE NAMED].

9. ADDITIONAL INFORMATION

    For additional information regarding this offering, please refer to the
    base Prospectus dated [DATE] and the Pooling and Servicing Agreement.

    This Prospectus Supplement does not constitute an offer to sell or a
    solicitation of an offer to buy the Securities in any jurisdiction where
    such offer or solicitation would be unlawful.

{content['originator_name']}
{content['effective_date']}
"""
    
    return text.strip()
