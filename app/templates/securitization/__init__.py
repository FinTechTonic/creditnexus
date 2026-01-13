"""Securitization template generation module."""

from app.templates.securitization.psa_template import generate_psa_template
from app.templates.securitization.trust_agreement_template import generate_trust_agreement_template
from app.templates.securitization.prospectus_template import generate_prospectus_template

__all__ = [
    'generate_psa_template',
    'generate_trust_agreement_template',
    'generate_prospectus_template',
]
