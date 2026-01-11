"""Service for extracting structured profile data from documents."""

import logging
from typing import Optional, List, Union, Dict, Any
from pathlib import Path
import tempfile
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.user_profile import UserProfileData
from app.chains.image_extraction_chain import ImageExtractionService, get_image_extraction_service
from app.core.llm_client import get_chat_model

logger = logging.getLogger(__name__)


class ProfileExtractionService:
    """Service for extracting structured profile data from documents.
    
    Supports:
    - PDF documents (text extraction)
    - Image files (OCR)
    - Multiple file formats
    """
    
    def __init__(self, db: Session):
        """Initialize the profile extraction service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.image_service = get_image_extraction_service()
        self.llm = get_chat_model()
    
    def extract_text_from_document(
        self,
        file_content: bytes,
        filename: str,
        file_type: Optional[str] = None
    ) -> str:
        """Extract text from a document file.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            file_type: Optional file type hint (pdf, image, etc.)
            
        Returns:
            Extracted text string
            
        Raises:
            ValueError: If file type is unsupported or extraction fails
        """
        # Determine file type from extension if not provided
        if not file_type:
            ext = Path(filename).suffix.lower()
            if ext == '.pdf':
                file_type = 'pdf'
            elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp']:
                file_type = 'image'
            else:
                file_type = 'unknown'
        
        logger.info(f"Extracting text from {file_type} file: {filename}")
        
        if file_type == 'pdf':
            try:
                text = extract_text_from_pdf(file_content)
                logger.info(f"Extracted {len(text)} characters from PDF")
                return text
            except Exception as e:
                logger.error(f"PDF extraction failed: {e}")
                raise ValueError(f"Failed to extract text from PDF: {e}") from e
        
        elif file_type == 'image':
            try:
                text = self.image_service.extract_text_from_bytes(
                    image_bytes=file_content,
                    filename=filename
                )
                logger.info(f"Extracted {len(text)} characters from image via OCR")
                return text
            except Exception as e:
                logger.error(f"Image OCR failed: {e}")
                raise ValueError(f"Failed to extract text from image: {e}") from e
        
        else:
            raise ValueError(f"Unsupported file type: {file_type}. Supported types: pdf, image")
    
    def extract_profile_from_text(
        self,
        text: str,
        role: Optional[str] = None,
        existing_profile: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> UserProfileData:
        """Extract structured profile data from text using LLM.
        
        Args:
            text: Extracted text from document
            role: Optional user role to guide extraction (applicant, banker, etc.)
            existing_profile: Optional existing profile data to merge with
            max_retries: Maximum number of retry attempts
            
        Returns:
            UserProfileData model instance
            
        Raises:
            ValueError: If extraction fails after retries
        """
        from app.chains.profile_extraction_chain import extract_profile_data
        
        logger.info(f"Extracting profile data from {len(text)} characters of text")
        
        # Extract profile data using the chain
        result = extract_profile_data(
            text=text,
            role=role,
            existing_profile=existing_profile,
            max_retries=max_retries
        )
        
        # Add metadata
        result.extraction_date = datetime.utcnow().isoformat()
        result.raw_extracted_text = text[:1000]  # Store first 1000 chars for reference
        
        logger.info("Successfully extracted profile data")
        return result
    
    def extract_profile_from_document(
        self,
        file_content: bytes,
        filename: str,
        role: Optional[str] = None,
        existing_profile: Optional[Dict[str, Any]] = None,
        file_type: Optional[str] = None
    ) -> UserProfileData:
        """Extract structured profile data from a document file.
        
        This is a convenience method that combines text extraction and profile extraction.
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            role: Optional user role to guide extraction
            existing_profile: Optional existing profile data to merge with
            file_type: Optional file type hint
            
        Returns:
            UserProfileData model instance
            
        Raises:
            ValueError: If extraction fails
        """
        # Extract text from document
        text = self.extract_text_from_document(
            file_content=file_content,
            filename=filename,
            file_type=file_type
        )
        
        if not text or len(text.strip()) == 0:
            raise ValueError(f"No text extracted from document: {filename}")
        
        # Extract profile data from text
        profile_data = self.extract_profile_from_text(
            text=text,
            role=role,
            existing_profile=existing_profile
        )
        
        # Set source document filename
        profile_data.extracted_from = filename
        
        return profile_data
    
    def extract_profile_from_multiple_documents(
        self,
        files: List[tuple[bytes, str]],
        role: Optional[str] = None,
        existing_profile: Optional[Dict[str, Any]] = None
    ) -> UserProfileData:
        """Extract profile data from multiple documents and merge results.
        
        Args:
            files: List of tuples (file_content, filename)
            role: Optional user role to guide extraction
            existing_profile: Optional existing profile data to merge with
            
        Returns:
            Merged UserProfileData model instance
        """
        logger.info(f"Extracting profile from {len(files)} document(s)")
        
        all_text_parts = []
        extracted_profiles = []
        
        # Extract text from all documents
        for file_content, filename in files:
            try:
                text = self.extract_text_from_document(
                    file_content=file_content,
                    filename=filename
                )
                if text and text.strip():
                    all_text_parts.append(f"\n\n--- Document: {filename} ---\n\n{text}")
            except Exception as e:
                logger.warning(f"Failed to extract text from {filename}: {e}")
                continue
        
        if not all_text_parts:
            raise ValueError("No text extracted from any document")
        
        # Combine all text
        combined_text = "\n".join(all_text_parts)
        
        # Extract profile from combined text
        profile_data = self.extract_profile_from_text(
            text=combined_text,
            role=role,
            existing_profile=existing_profile
        )
        
        # Set source documents
        profile_data.extracted_from = ", ".join([fname for _, fname in files])
        
        return profile_data
    
    def merge_profiles(
        self,
        profile1: UserProfileData,
        profile2: UserProfileData
    ) -> UserProfileData:
        """Merge two profile data objects, with profile2 taking precedence.
        
        Args:
            profile1: First profile (base)
            profile2: Second profile (overrides)
            
        Returns:
            Merged UserProfileData
        """
        # Convert to dicts for easier merging
        dict1 = profile1.model_dump(exclude_none=True)
        dict2 = profile2.model_dump(exclude_none=True)
        
        # Merge dictionaries (profile2 overrides profile1)
        merged_dict = {**dict1, **dict2}
        
        # For nested objects, merge them too
        if 'contact' in dict1 and 'contact' in dict2:
            merged_dict['contact'] = {**dict1['contact'], **dict2['contact']}
        if 'personal_address' in dict1 and 'personal_address' in dict2:
            merged_dict['personal_address'] = {**dict1['personal_address'], **dict2['personal_address']}
        if 'professional' in dict1 and 'professional' in dict2:
            merged_dict['professional'] = {**dict1['professional'], **dict2['professional']}
        if 'company' in dict1 and 'company' in dict2:
            merged_dict['company'] = {**dict1['company'], **dict2['company']}
        if 'financial' in dict1 and 'financial' in dict2:
            merged_dict['financial'] = {**dict1['financial'], **dict2['financial']}
        
        # Reconstruct UserProfileData
        return UserProfileData(**merged_dict)
