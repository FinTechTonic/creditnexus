"""
CDM Event Service for persisting and retrieving CDM events.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.models import Deal
from app.services.file_storage_service import FileStorageService

logger = logging.getLogger(__name__)


class CDMEventService:
    """Service for persisting and retrieving CDM events."""
    
    def __init__(self, db: Session):
        self.db = db
        self.file_storage = FileStorageService()
    
    def persist_event(
        self,
        deal_id: int,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[int] = None
    ) -> str:
        """Persist a CDM event for a deal.
        
        Args:
            deal_id: Deal ID
            event_type: Type of CDM event (e.g., "SignatureEvent", "DocumentationEvent")
            event_data: Full CDM event dictionary
            user_id: Optional user ID (will use deal applicant if not provided)
            
        Returns:
            Path to stored event file
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Use deal applicant as user_id if not provided
        if user_id is None:
            user_id = deal.applicant_id
        
        # Generate event ID
        event_id = f"{event_type}_{deal_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Store event using file storage
        event_path = self.file_storage.store_cdm_event(
            user_id=user_id,
            deal_id=deal.deal_id,
            event_id=event_id,
            event_data=event_data
        )
        
        logger.info(f"Persisted CDM event {event_type} for deal {deal_id} at {event_path}")
        
        return event_path
    
    def get_events_for_deal(
        self,
        deal_id: int,
        event_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all CDM events for a deal.
        
        Args:
            deal_id: Deal ID
            event_type: Optional filter by event type
            
        Returns:
            List of CDM event dictionaries
        """
        deal = self.db.query(Deal).filter(Deal.id == deal_id).first()
        if not deal:
            raise ValueError(f"Deal {deal_id} not found")
        
        # Get events from file storage
        events_dir = self.file_storage.base_storage_path / str(deal.applicant_id) / deal.deal_id / "events"
        
        if not events_dir.exists():
            return []
        
        events = []
        for event_file in events_dir.glob("*.json"):
            try:
                import json
                with open(event_file, 'r', encoding='utf-8') as f:
                    event_data = json.load(f)
                    
                    # Filter by event type if specified
                    if event_type is None or event_data.get("eventType") == event_type:
                        events.append(event_data)
            except Exception as e:
                logger.warning(f"Failed to read event file {event_file}: {e}")
                continue
        
        # Sort by event date (most recent first)
        events.sort(key=lambda e: e.get("eventDate", ""), reverse=True)
        
        return events
    
    def get_signature_events_for_deal(self, deal_id: int) -> List[Dict[str, Any]]:
        """Get all signature events for a deal.
        
        Args:
            deal_id: Deal ID
            
        Returns:
            List of signature event dictionaries
        """
        return self.get_events_for_deal(deal_id, event_type="SignatureEvent")
    
    def get_documentation_events_for_deal(self, deal_id: int) -> List[Dict[str, Any]]:
        """Get all documentation events for a deal.
        
        Args:
            deal_id: Deal ID
            
        Returns:
            List of documentation event dictionaries
        """
        return self.get_events_for_deal(deal_id, event_type="DocumentationEvent")
