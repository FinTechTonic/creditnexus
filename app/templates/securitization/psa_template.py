"""
Pooling and Servicing Agreement (PSA) template generator for securitization.

Generates PSA documents from securitization pool CDM data.
"""

import logging
from datetime import date, datetime
from typing import Dict, Any, Optional
from decimal import Decimal

from app.models.cdm import SecuritizationPool as CDMSecuritizationPool, Currency

logger = logging.getLogger(__name__)


def generate_psa_template(
    pool_data: Dict[str, Any],
    pool_cdm: Optional[CDMSecuritizationPool] = None
) -> Dict[str, Any]:
    """
    Generate Pooling and Servicing Agreement template data from securitization pool.
    
    Args:
        pool_data: Pool data dictionary from database
        pool_cdm: Optional CDM SecuritizationPool model
        
    Returns:
        Dictionary with PSA template fields and content
    """
    pool_name = pool_data.get('pool_name', '')
    pool_id = pool_data.get('pool_id', '')
    pool_type = pool_data.get('pool_type', 'ABS')
    total_value = pool_data.get('total_pool_value', '0')
    currency = pool_data.get('currency', 'USD')
    effective_date = pool_data.get('created_at', datetime.now().isoformat())
    
    # Extract parties from CDM if available
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
    
    # Extract tranches
    tranches = pool_data.get('tranches', [])
    tranche_summary = []
    for tranche in tranches:
        tranche_summary.append({
            'name': tranche.get('tranche_name', ''),
            'class': tranche.get('tranche_class', ''),
            'size': str(tranche.get('size', {}).get('amount', 0) if isinstance(tranche.get('size'), dict) else tranche.get('size', 0)),
            'interest_rate': str(tranche.get('interest_rate', 0)),
            'risk_rating': tranche.get('risk_rating', 'NR'),
            'priority': str(tranche.get('payment_priority', 999))
        })
    
    # Extract underlying assets
    assets = pool_data.get('assets', [])
    asset_summary = []
    for asset in assets:
        asset_summary.append({
            'type': asset.get('asset_type', ''),
            'id': asset.get('asset_id', ''),
            'value': str(asset.get('asset_value', 0)),
            'currency': asset.get('currency', currency)
        })
    
    # Generate PSA content
    psa_content = {
        'title': f'Pooling and Servicing Agreement - {pool_name}',
        'pool_name': pool_name,
        'pool_id': pool_id,
        'pool_type': pool_type,
        'effective_date': effective_date,
        'total_pool_value': str(total_value),
        'currency': currency,
        'originator_name': originator_name,
        'trustee_name': trustee_name,
        'servicer_name': servicer_name,
        'tranches': tranche_summary,
        'underlying_assets': asset_summary,
        'tranche_count': len(tranches),
        'asset_count': len(assets),
    }
    
    # Generate full document text (can be used for Word template or PDF generation)
    psa_text = _generate_psa_document_text(psa_content)
    psa_content['document_text'] = psa_text
    
    logger.info(f"Generated PSA template for pool {pool_id}")
    return psa_content


def _generate_psa_document_text(content: Dict[str, Any]) -> str:
    """Generate full PSA document text."""
    
    text = f"""
POOLING AND SERVICING AGREEMENT

{content['title']}

This Pooling and Servicing Agreement (the "Agreement") is entered into as of {content['effective_date']}, 
by and between {content['originator_name']} (the "Originator"), {content['trustee_name']} (the "Trustee"), 
and {content['servicer_name']} (the "Servicer").

1. DEFINITIONS

1.1 Pool Information
    Pool Name: {content['pool_name']}
    Pool ID: {content['pool_id']}
    Pool Type: {content['pool_type']}
    Total Pool Value: {content['currency']} {content['total_pool_value']}
    Effective Date: {content['effective_date']}

1.2 Parties
    Originator: {content['originator_name']}
    Trustee: {content['trustee_name']}
    Servicer: {content['servicer_name']}

2. POOL STRUCTURE

2.1 Tranche Structure
    The securitization pool consists of {content['tranche_count']} tranche(s):
"""
    
    for i, tranche in enumerate(content['tranches'], 1):
        text += f"""
    Tranche {i}: {tranche['name']}
        - Class: {tranche['class']}
        - Size: {tranche['currency']} {tranche['size']}
        - Interest Rate: {tranche['interest_rate']}%
        - Risk Rating: {tranche['risk_rating']}
        - Payment Priority: {tranche['priority']}
"""
    
    text += f"""
2.2 Underlying Assets
    The pool is backed by {content['asset_count']} underlying asset(s):
"""
    
    for i, asset in enumerate(content['underlying_assets'], 1):
        text += f"""
    Asset {i}:
        - Type: {asset['type']}
        - ID: {asset['id']}
        - Value: {asset['currency']} {asset['value']}
"""
    
    text += """
3. SERVICING PROVISIONS

3.1 Servicing Responsibilities
    The Servicer shall be responsible for:
    - Collection of payments from underlying assets
    - Distribution of payments to tranche holders according to payment waterfall
    - Reporting and compliance obligations
    - Asset management and monitoring

3.2 Payment Waterfall
    Payments shall be distributed in accordance with the payment priority of each tranche,
    with senior tranches receiving payments before junior tranches.

4. REPRESENTATIONS AND WARRANTIES

    Each party represents and warrants that:
    - It has full power and authority to enter into this Agreement
    - This Agreement constitutes a valid and binding obligation
    - All information provided is accurate and complete

5. TERM AND TERMINATION

    This Agreement shall remain in effect until all obligations under the securitization
    have been satisfied or the pool has been liquidated.

6. GOVERNING LAW

    This Agreement shall be governed by and construed in accordance with applicable
    securities laws and regulations.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

{content['originator_name']}                    {content['trustee_name']}
_________________________                    _________________________
Originator                                   Trustee

{content['servicer_name']}
_________________________
Servicer
"""
    
    return text.strip()
