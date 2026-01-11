"""
File storage service for deal document management.

This service handles creating deal folder structures and managing
documents within deal-specific directories.
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FileStorageService:
    """Service for managing deal file storage."""
    
    def __init__(self, base_storage_path: str = "storage/deals"):
        """
        Initialize file storage service.
        
        Args:
            base_storage_path: Base path for deal storage (relative to project root)
        """
        self.base_storage_path = Path(base_storage_path)
        self.base_storage_path.mkdir(parents=True, exist_ok=True)
    
    def create_deal_folder(self, user_id: int, deal_id: str) -> str:
        """
        Create folder structure for a deal.
        
        Structure: storage/deals/{user_id}/{deal_id}/
        Subdirectories: documents/, extractions/, generated/, notes/, events/
        
        Args:
            user_id: ID of the user/applicant
            deal_id: Unique deal identifier
            
        Returns:
            Path to the created deal folder
        """
        deal_folder = self.base_storage_path / str(user_id) / deal_id
        
        # Create main deal folder
        deal_folder.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        subdirs = ["documents", "extractions", "generated", "notes", "events"]
        for subdir in subdirs:
            (deal_folder / subdir).mkdir(exist_ok=True)
        
        folder_path = str(deal_folder.absolute())
        logger.info(f"Created deal folder structure: {folder_path}")
        
        return folder_path
    
    def store_deal_document(
        self,
        user_id: int,
        deal_id: str,
        document_id: int,
        filename: str,
        content: bytes,
        subdirectory: str = "documents"
    ) -> str:
        """
        Store a document in the deal folder.
        
        Args:
            user_id: ID of the user/applicant
            deal_id: Unique deal identifier
            document_id: ID of the document
            filename: Name of the file to store
            content: File content as bytes
            subdirectory: Subdirectory to store in (documents, extractions, generated, notes)
            
        Returns:
            Path to the stored file
        """
        deal_folder = self.base_storage_path / str(user_id) / deal_id
        
        # Ensure deal folder exists
        if not deal_folder.exists():
            self.create_deal_folder(user_id, deal_id)
        
        # Determine subdirectory
        if subdirectory not in ["documents", "extractions", "generated", "notes", "events"]:
            subdirectory = "documents"
        
        target_dir = deal_folder / subdirectory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Store file with document_id prefix to avoid conflicts
        file_path = target_dir / f"{document_id}_{filename}"
        
        with open(file_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Stored document {document_id} to {file_path}")
        
        return str(file_path.absolute())
    
    def get_deal_documents(
        self,
        user_id: int,
        deal_id: str,
        subdirectory: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List all documents for a deal.
        
        Args:
            user_id: ID of the user/applicant
            deal_id: Unique deal identifier
            subdirectory: Optional subdirectory to filter by
            
        Returns:
            List of document metadata dictionaries
        """
        deal_folder = self.base_storage_path / str(user_id) / deal_id
        
        if not deal_folder.exists():
            return []
        
        documents = []
        
        # Determine which subdirectories to search
        if subdirectory:
            subdirs = [subdirectory] if subdirectory in ["documents", "extractions", "generated", "notes", "events"] else ["documents"]
        else:
            subdirs = ["documents", "extractions", "generated", "notes", "events"]
        
        for subdir in subdirs:
            subdir_path = deal_folder / subdir
            if subdir_path.exists():
                for file_path in subdir_path.iterdir():
                    if file_path.is_file():
                        stat = file_path.stat()
                        documents.append({
                            "filename": file_path.name,
                            "path": str(file_path.absolute()),
                            "subdirectory": subdir,
                            "size": stat.st_size,
                            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        })
        
        return documents
    
    def archive_deal(self, user_id: int, deal_id: str) -> str:
        """
        Archive a deal by moving it to an archive folder.
        
        Args:
            user_id: ID of the user/applicant
            deal_id: Unique deal identifier
            
        Returns:
            Path to the archived deal folder
        """
        deal_folder = self.base_storage_path / str(user_id) / deal_id
        archive_folder = self.base_storage_path / "archive" / str(user_id) / deal_id
        
        if not deal_folder.exists():
            logger.warning(f"Deal folder does not exist: {deal_folder}")
            return str(archive_folder.absolute())
        
        # Create archive directory structure
        archive_folder.parent.mkdir(parents=True, exist_ok=True)
        
        # Move deal folder to archive
        import shutil
        shutil.move(str(deal_folder), str(archive_folder))
        
        logger.info(f"Archived deal {deal_id} to {archive_folder}")
        
        return str(archive_folder.absolute())
    
    def store_deal_note(
        self,
        user_id: int,
        deal_id: str,
        note_id: int,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a note for a deal.
        
        Args:
            user_id: ID of the user/applicant
            deal_id: Unique deal identifier
            note_id: ID of the note
            content: Note content
            metadata: Optional metadata (author, timestamp, etc.)
            
        Returns:
            Path to the stored note file
        """
        deal_folder = self.base_storage_path / str(user_id) / deal_id
        
        # Ensure deal folder exists
        if not deal_folder.exists():
            self.create_deal_folder(user_id, deal_id)
        
        notes_dir = deal_folder / "notes"
        notes_dir.mkdir(parents=True, exist_ok=True)
        
        # Store note as JSON file
        import json
        note_data = {
            "note_id": note_id,
            "content": content,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }
        
        note_file = notes_dir / f"{note_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(note_file, 'w', encoding='utf-8') as f:
            json.dump(note_data, f, indent=2)
        
        logger.info(f"Stored note {note_id} to {note_file}")
        
        return str(note_file.absolute())
    
    def store_cdm_event(
        self,
        user_id: int,
        deal_id: str,
        event_id: str,
        event_data: Dict[str, Any]
    ) -> str:
        """
        Store a CDM event for a deal.
        
        Args:
            user_id: ID of the user/applicant
            deal_id: Unique deal identifier
            event_id: Unique event identifier
            event_data: CDM event data dictionary
            
        Returns:
            Path to the stored event file
        """
        deal_folder = self.base_storage_path / str(user_id) / deal_id
        
        # Ensure deal folder exists
        if not deal_folder.exists():
            self.create_deal_folder(user_id, deal_id)
        
        events_dir = deal_folder / "events"
        events_dir.mkdir(parents=True, exist_ok=True)
        
        # Store event as JSON file
        import json
        event_file = events_dir / f"{event_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(event_file, 'w', encoding='utf-8') as f:
            json.dump(event_data, f, indent=2)
        
        logger.info(f"Stored CDM event {event_id} to {event_file}")
        
        return str(event_file.absolute())
