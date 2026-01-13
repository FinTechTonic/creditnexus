"""
Trust Agreement template generator for securitization.

Generates Trust Agreement documents from securitization pool CDM data.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

from app.models.cdm import SecuritizationPool as CDMSecuritizationPool

logger = logging.getLogger(__name__)


def generate_trust_agreement_template(
    pool_data: Dict[str, Any],
    pool_cdm: Optional[CDMSecuritizationPool] = None
) -> Dict[str, Any]:
    """
    Generate Trust Agreement template data from securitization pool.
    
    Args:
        pool_data: Pool data dictionary from database
        pool_cdm: Optional CDM SecuritizationPool model
        
    Returns:
        Dictionary with Trust Agreement template fields and content
    """
    pool_name = pool_data.get('pool_name', '')
    pool_id = pool_data.get('pool_id', '')
    pool_type = pool_data.get('pool_type', 'ABS')
    total_value = pool_data.get('total_pool_value', '0')
    currency = pool_data.get('currency', 'USD')
    effective_date = pool_data.get('created_at', datetime.now().isoformat())
    
    # Extract parties
    trustee_name = "Trustee"
    originator_name = "Originator"
    
    if pool_cdm:
        if pool_cdm.trustee:
            trustee_name = pool_cdm.trustee.name or trustee_name
        if pool_cdm.originator:
            originator_name = pool_cdm.originator.name or originator_name
    
    # Extract tranches
    tranches = pool_data.get('tranches', [])
    tranche_details = []
    for tranche in tranches:
        tranche_details.append({
            'name': tranche.get('tranche_name', ''),
            'class': tranche.get('tranche_class', ''),
            'size': str(tranche.get('size', {}).get('amount', 0) if isinstance(tranche.get('size'), dict) else tranche.get('size', 0)),
            'interest_rate': str(tranche.get('interest_rate', 0)),
            'risk_rating': tranche.get('risk_rating', 'NR')
        })
    
    # Generate Trust Agreement content
    trust_content = {
        'title': f'Trust Agreement - {pool_name}',
        'pool_name': pool_name,
        'pool_id': pool_id,
        'pool_type': pool_type,
        'effective_date': effective_date,
        'total_pool_value': str(total_value),
        'currency': currency,
        'trustee_name': trustee_name,
        'originator_name': originator_name,
        'tranches': tranche_details,
        'tranche_count': len(tranches),
    }
    
    # Generate full document text
    trust_text = _generate_trust_document_text(trust_content)
    trust_content['document_text'] = trust_text
    
    logger.info(f"Generated Trust Agreement template for pool {pool_id}")
    return trust_content


def _generate_trust_document_text(content: Dict[str, Any]) -> str:
    """Generate full Trust Agreement document text."""
    
    text = f"""
TRUST AGREEMENT

{content['title']}

This Trust Agreement (the "Agreement") is entered into as of {content['effective_date']}, 
by and between {content['originator_name']} (the "Depositor") and {content['trustee_name']} (the "Trustee").

1. ESTABLISHMENT OF TRUST

1.1 Trust Name
    The trust established hereunder shall be known as "{content['pool_name']} Trust"
    (the "Trust").

1.2 Trust Property
    The Trust shall hold the securitization pool assets with a total value of
    {content['currency']} {content['total_pool_value']}.

2. TRUSTEE DUTIES AND RESPONSIBILITIES

2.1 Fiduciary Duties
    The Trustee shall act in a fiduciary capacity and shall:
    - Hold and safeguard trust assets
    - Distribute payments to tranche holders according to the payment waterfall
    - Maintain accurate records and provide reporting
    - Comply with all applicable laws and regulations

2.2 Investment of Trust Assets
    The Trustee may invest trust assets in accordance with the terms of the
    Pooling and Servicing Agreement and applicable law.

3. TRANCHE STRUCTURE

    The Trust shall issue {content['tranche_count']} tranche(s) of securities:
"""
    
    for i, tranche in enumerate(content['tranches'], 1):
        text += f"""
    Tranche {i}: {tranche['name']}
        - Class: {tranche['class']}
        - Size: {content['currency']} {tranche['size']}
        - Interest Rate: {tranche['interest_rate']}%
        - Risk Rating: {tranche['risk_rating']}
"""
    
    text += """
4. DISTRIBUTIONS

4.1 Payment Distribution
    The Trustee shall distribute payments received from the underlying assets
    to tranche holders in accordance with the payment priority established
    in the Pooling and Servicing Agreement.

4.2 Reporting
    The Trustee shall provide regular reports to tranche holders regarding:
    - Payment distributions
    - Trust asset performance
    - Compliance status

5. TERM AND TERMINATION

    This Trust shall continue until all obligations have been satisfied or
    the trust assets have been liquidated.

6. GOVERNING LAW

    This Agreement shall be governed by and construed in accordance with
    applicable trust and securities laws.

IN WITNESS WHEREOF, the parties have executed this Agreement as of the date first written above.

{content['originator_name']}                    {content['trustee_name']}
_________________________                    _________________________
Depositor                                   Trustee
"""
    
    return text.strip()
