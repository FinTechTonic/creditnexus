"""API routes for .nexus file generation and upload."""

import uuid
import hashlib
import logging
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.db import get_db
from app.auth.jwt_auth import get_current_user
from app.db.models import User, Deal, Document
from app.utils.nexus_file_generator import NexusFileGenerator
from app.utils.nexus_file_parser import NexusFileParser
from app.services.workflow_delegation_service import WorkflowDelegationService
from app.services.permission_key_service import PermissionKeyService
from app.services.sharing_event_service import SharingEventService
from app.services.file_storage_service import FileStorageService
from app.services.cdm_payload_generator import get_deal_cdm_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/nexus", tags=["nexus"])


class GenerateNexusFileRequest(BaseModel):
    """Request to generate .nexus file."""

    workflow_type: str = Field(..., description="Workflow type")
    deal_id: Optional[int] = Field(None, description="Deal ID")
    document_id: Optional[int] = Field(None, description="Document ID")
    workflow_metadata: Optional[dict] = Field(None, description="Workflow metadata")
    file_categories: Optional[List[str]] = Field(None, description="File categories to include")
    file_document_ids: Optional[List[int]] = Field(None, description="Specific document IDs")
    receiver_email: Optional[str] = Field(None, description="Receiver email")
    receiver_wallet_address: Optional[str] = Field(None, description="Receiver wallet address")
    permission_keys: Optional[dict] = Field(None, description="Permission keys to include")
    expires_in_hours: int = Field(72, description="Link expiration in hours")
    download_ttl_hours: Optional[int] = Field(None, description="Download TTL in hours")
    include_files: bool = Field(True, description="Whether to embed files")
    max_embedded_size: int = Field(10 * 1024 * 1024, description="Max size for embedded files")


@router.post("/generate")
async def generate_nexus_file(
    request: GenerateNexusFileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate .nexus file for sharing.

    Returns:
        .nexus file as download
    """
    # Get deal data if deal_id provided
    deal_data = {}
    cdm_payload = {}
    if request.deal_id:
        deal = db.query(Deal).filter(Deal.id == request.deal_id).first()
        if not deal:
            raise HTTPException(status_code=404, detail="Deal not found")

        deal_data = {
            "deal_id": deal.deal_id,
            "status": deal.status,
            "deal_type": deal.deal_type,
            "deal_data": deal.deal_data or {},
        }
        cdm_payload = get_deal_cdm_payload(db, deal)

    # Get file references
    file_references = []
    if request.include_files and request.deal_id:
        delegation_service = WorkflowDelegationService(db)
        file_references = delegation_service._get_file_references(
            deal_id=request.deal_id,
            file_categories=request.file_categories,
            file_document_ids=request.file_document_ids,
        )

    # Get sender info (User has organization_identifier, not organization_id)
    sender_info = {
        "user_id": current_user.id,
        "email": current_user.email,
        "name": current_user.display_name or current_user.email,
        "organization": getattr(current_user, "organization_identifier", None),
    }

    # Get receiver info
    receiver_info = {}
    if request.receiver_email:
        receiver_info["email"] = request.receiver_email
    if request.receiver_wallet_address:
        receiver_info["wallet_address"] = request.receiver_wallet_address

    # Generate workflow ID
    workflow_id = str(uuid.uuid4())

    # Generate .nexus file
    generator = NexusFileGenerator()
    nexus_bytes = generator.generate_nexus_file(
        workflow_type=request.workflow_type,
        workflow_id=workflow_id,
        deal_id=request.deal_id,
        deal_data=deal_data,
        cdm_payload=cdm_payload,
        workflow_metadata=request.workflow_metadata,
        file_references=file_references,
        sender_info=sender_info,
        receiver_info=receiver_info,
        permission_keys=request.permission_keys,
        expires_in_hours=request.expires_in_hours,
        download_ttl_hours=request.download_ttl_hours,
        include_files=request.include_files,
        max_embedded_size=request.max_embedded_size,
    )

    # Create send event and notarize
    sharing_service = SharingEventService(db)
    sharing_event = sharing_service.create_send_event(
        sender_user_id=current_user.id,
        sharing_method="nexus_file",
        file_data=nexus_bytes,
        workflow_id=workflow_id,
        deal_id=request.deal_id,
        receiver_email=request.receiver_email,
        receiver_wallet_address=request.receiver_wallet_address,
    )

    # Return .nexus file
    filename = f"deal_share_{request.deal_id or 'workflow'}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.nexus"
    return Response(
        content=nexus_bytes,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Sharing-Event-Id": sharing_event.event_id,
            "X-Blockchain-Tx-Hash": sharing_event.blockchain_tx_hash or "",
        }
    )


@router.post("/upload")
async def upload_nexus_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload and parse .nexus file.

    Returns:
        Parsed workflow data
    """
    # Validate file extension
    if not file.filename or not file.filename.endswith('.nexus'):
        raise HTTPException(status_code=400, detail="File must have .nexus extension")

    # Read file
    file_bytes = await file.read()

    # Parse .nexus file
    parser = NexusFileParser()
    try:
        parsed_data = parser.parse_nexus_file(file_bytes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse .nexus file: {str(e)}")

    # Verify permissions if provided
    permissions = parsed_data.get('permissions')
    if permissions:
        permission_service = PermissionKeyService(db)
        # Verify wallet or application key
        # This would need to be implemented based on how permissions are structured
        # For now, we'll just log that permissions were found
        logger.info(f"Permissions found in .nexus file: {len(permissions.get('wallet_keys', []))} wallet keys")

    # Process workflow
    delegation_service = WorkflowDelegationService(db)
    metadata = parsed_data.get('metadata', {})
    workflow_id = metadata.get('workflow_id')

    # Store embedded files
    file_storage = FileStorageService()
    embedded_files = parsed_data.get('embedded_files', {})
    stored_files = []
    for filename, file_info in embedded_files.items():
        try:
            # Store file using FileStorageService
            deal_id_str = metadata.get('deal_id')
            if deal_id_str:
                # Get deal to find user_id
                deal = db.query(Deal).filter(Deal.deal_id == deal_id_str).first()
                if deal:
                    file_path = file_storage.store_deal_document(
                        user_id=deal.applicant_id,
                        deal_id=deal_id_str,
                        document_id=0,  # Would need to create document record
                        filename=filename,
                        content=file_info['content'],
                        subdirectory="documents"
                    )
                    stored_files.append({
                        "filename": filename,
                        "path": file_path,
                        "size": file_info['size']
                    })
        except Exception as e:
            logger.warning(f"Failed to store embedded file {filename}: {e}")

    # Download large files if TTL not expired
    large_file_references = parsed_data.get('large_file_references', [])
    downloaded_files = []
    for file_ref in large_file_references:
        download_ttl = file_ref.get('download_ttl')
        if download_ttl:
            ttl_dt = datetime.fromisoformat(download_ttl.replace('Z', '+00:00'))
            if datetime.utcnow() > ttl_dt.replace(tzinfo=None):
                logger.warning(f"Download TTL expired for {file_ref['filename']}")
                continue

        # Download file (would need to implement download with permission keys)
        logger.info(f"Large file reference found: {file_ref['filename']} ({file_ref.get('size', 0)} bytes)")

    # Create receive event and notarize
    sharing_service = SharingEventService(db)
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    receive_event = sharing_service.create_receive_event(
        receiver_user_id=current_user.id,
        sharing_method="nexus_file",
        file_data=file_bytes,
        file_hash=file_hash,
        workflow_id=workflow_id,
        deal_id=metadata.get('deal_id'),
    )

    logger.info(
        f"Uploaded and parsed .nexus file: {len(embedded_files)} embedded files, "
        f"{len(large_file_references)} references"
    )

    return {
        "status": "success",
        "workflow_id": workflow_id,
        "workflow_type": metadata.get('workflow_type'),
        "deal_id": metadata.get('deal_id'),
        "files_processed": len(stored_files) + len(downloaded_files),
        "embedded_files": len(embedded_files),
        "large_file_references": len(large_file_references),
        "receive_event_id": receive_event.event_id,
        "blockchain_tx_hash": receive_event.blockchain_tx_hash,
    }
