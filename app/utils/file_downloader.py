"""Utility for downloading files from URLs and storing in local Postgres."""

import logging
import httpx
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


async def download_file_from_url(
    url: str,
    deal_id: int,
    filename: str,
    category: str,
    subdirectory: str,
    db: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Download file from URL and store in local Postgres.
    
    Args:
        url: File download URL
        deal_id: Deal ID
        filename: Original filename
        category: File category
        subdirectory: Storage subdirectory
        db: Optional database session (if None, creates new session)
    
    Returns:
        File metadata dict or None if download fails
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            file_content = response.content
            
            # Store using FileStorageService
            from app.services.file_storage_service import FileStorageService
            from app.db.models import Deal
            
            # Get database session if not provided
            if db is None:
                from app.db import SessionLocal
                db = SessionLocal()
                close_db = True
            else:
                close_db = False
            
            try:
                # Get deal to get applicant_id
                deal = db.query(Deal).filter(Deal.id == deal_id).first()
                if not deal:
                    logger.error(f"Deal {deal_id} not found for file download")
                    return None
                
                file_storage = FileStorageService()
                
                # Store file in deal folder
                file_path = file_storage.store_deal_document(
                    user_id=deal.applicant_id,
                    deal_id=deal.deal_id,
                    document_id=0,  # Will be updated when document is created
                    filename=filename,
                    content=file_content,
                    subdirectory=subdirectory
                )
                
                # Get file size
                file_size = len(file_content)
                
                return {
                    "filename": filename,
                    "path": file_path,
                    "size": file_size,
                    "category": category,
                    "subdirectory": subdirectory,
                    "deal_id": deal_id
                }
            finally:
                if close_db:
                    db.close()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error downloading file from {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to download file from {url}: {e}")
        return None
