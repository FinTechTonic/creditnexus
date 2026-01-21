"""
SFP Bundler Service for Structured Financial Products.

Creates Merkle trees from CDM data, signatures, and filings,
then anchors the root hash to blockchain via SecuritizationNotarization.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import Deal, Document, DocumentFiling, DocumentSignature, DocumentVersion

logger = logging.getLogger(__name__)


class SFPBundlerService:
    """Service for bundling Structured Financial Products (SFPs)."""

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _hash_data(data: bytes) -> str:
        """Compute SHA-256 hash, return hex with 0x prefix (64 hex chars)."""
        h = hashlib.sha256(data).hexdigest()
        return "0x" + h

    @staticmethod
    def _create_merkle_tree(items: List[str]) -> str:
        """Build a simple Merkle root from a list of hashes (each 0x + 64 hex)."""
        if not items:
            return SFPBundlerService._hash_data(b"")
        layer = [s.lower().replace("0x", "") for s in items]
        while len(layer) > 1:
            next_layer = []
            for i in range(0, len(layer), 2):
                left = layer[i]
                right = layer[i + 1] if i + 1 < len(layer) else layer[i]
                combined = hashlib.sha256((left + right).encode("utf-8")).hexdigest()
                next_layer.append(combined)
            layer = next_layer
        return "0x" + layer[0]

    def bundle_sfp(self, deal_id: int, market_event_type: str) -> Dict[str, Any]:
        """
        Build an SFP bundle for a deal: CDM hash, signature hashes, filing hashes, Merkle root.

        Args:
            deal_id: Deal ID
            market_event_type: e.g. "NDVI_COMPLIANCE"

        Returns:
            Dict with sfp_id, deal_id, merkle_root, cdm_hash, signature_hashes, filing_hashes,
            bundle_timestamp, market_event_type.
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")

        # CDM: from DocumentVersion.extracted_data for documents linked to this deal
        docs = self.db.query(Document).filter(Document.deal_id == deal_id).all()
        cdm_parts: List[Dict[str, Any]] = []
        for d in docs:
            # Use current version or latest
            ver = (
                self.db.query(DocumentVersion)
                .filter(DocumentVersion.document_id == d.id)
                .order_by(DocumentVersion.version_number.desc())
                .first()
            )
            if ver and ver.extracted_data:
                cdm_parts.append(ver.extracted_data)
        cdm_json = json.dumps(cdm_parts, sort_keys=True, default=str)
        cdm_hash = self._hash_data(cdm_json.encode("utf-8"))

        # Signatures: DocumentSignature for documents in this deal
        doc_ids = [d.id for d in docs]
        sigs: List[DocumentSignature] = []
        if doc_ids:
            sigs = self.db.query(DocumentSignature).filter(DocumentSignature.document_id.in_(doc_ids)).all()
        signature_hashes: List[str] = []
        for s in sigs:
            raw = s.signature_data or s.signature_provider_data or s.signers or {}
            if raw is not None:
                blob = json.dumps(raw, sort_keys=True, default=str).encode("utf-8")
                signature_hashes.append(self._hash_data(blob))

        # Filings: DocumentFiling for this deal
        filings = self.db.query(DocumentFiling).filter(DocumentFiling.deal_id == deal_id).all()
        filing_hashes: List[str] = []
        for f in filings:
            raw = f.filing_payload or f.filing_response or {}
            blob = json.dumps(raw, sort_keys=True, default=str).encode("utf-8")
            filing_hashes.append(self._hash_data(blob))

        all_hashes = [cdm_hash] + signature_hashes + filing_hashes
        merkle_root = self._create_merkle_tree(all_hashes)

        ts = datetime.utcnow()
        sfp_id = f"SFP_{deal_id}_{ts.strftime('%Y%m%d%H%M%S')}"

        return {
            "sfp_id": sfp_id,
            "deal_id": deal_id,
            "merkle_root": merkle_root,
            "cdm_hash": cdm_hash,
            "signature_hashes": signature_hashes,
            "filing_hashes": filing_hashes,
            "bundle_timestamp": ts.isoformat(),
            "market_event_type": market_event_type,
        }

    def anchor_sfp_to_blockchain(
        self,
        sfp_bundle: Dict[str, Any],
        signers: List[str],
    ) -> Dict[str, Any]:
        """
        Anchor the SFP Merkle root on-chain via SecuritizationNotarization.createNotarization.

        Args:
            sfp_bundle: Result from bundle_sfp (must contain sfp_id, merkle_root).
            signers: List of ethereum addresses (at least one required by contract).

        Returns:
            Dict with transaction_hash (or None), block_number (or None), success.
        """
        pool_id = sfp_bundle.get("sfp_id") or ""
        merkle_hex = (sfp_bundle.get("merkle_root") or "").replace("0x", "")
        if len(merkle_hex) != 64:
            return {"transaction_hash": None, "block_number": None, "success": False}

        try:
            from app.services.blockchain_service import BlockchainService
            from app.core.config import settings

            bc = BlockchainService()
            if not bc.web3 or not bc.is_connected():
                logger.info("Blockchain not connected; skipping SFP anchor on-chain")
                return {"transaction_hash": None, "block_number": None, "success": False}

            addr = settings.SECURITIZATION_NOTARIZATION_CONTRACT or (bc.get_contract_addresses() or {}).get("notarization")
            if not addr or not bc._contract_abis.get("notarization"):
                logger.info("SecuritizationNotarization contract not configured; skipping SFP anchor")
                return {"transaction_hash": None, "block_number": None, "success": False}

            contract = bc.web3.eth.contract(address=bc.web3.to_checksum_address(addr), abi=bc._contract_abis["notarization"])
            pool_hash_bytes = bytes.fromhex(merkle_hex)
            if len(pool_hash_bytes) != 32:
                return {"transaction_hash": None, "block_number": None, "success": False}

            signer_addrs = [bc.web3.to_checksum_address(s) for s in (signers or []) if s]
            if not signer_addrs:
                # Contract requires at least one signer; use deployer or a placeholder
                acc = bc._get_deployer_account()
                signer_addrs = [acc.address] if acc else [bc.web3.eth.accounts[0] if bc.web3.eth.accounts else "0x0000000000000000000000000000000000000001"]

            tx = contract.functions.createNotarization(pool_id, pool_hash_bytes, signer_addrs)
            built = tx.build_transaction({"from": bc.deployer_account.address} if bc.deployer_account else {})
            if not bc.deployer_account:
                return {"transaction_hash": None, "block_number": None, "success": False}
            signed = bc.web3.eth.account.sign_transaction(built, bc.deployer_account.key)
            sent = bc.web3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = bc.web3.eth.wait_for_transaction_receipt(sent)
            return {
                "transaction_hash": receipt.get("transactionHash") and bc.web3.to_hex(receipt["transactionHash"]),
                "block_number": receipt.get("blockNumber"),
                "success": True,
            }
        except Exception as e:
            logger.warning("SFP anchor to blockchain failed: %s", e)
            return {"transaction_hash": None, "block_number": None, "success": False}
