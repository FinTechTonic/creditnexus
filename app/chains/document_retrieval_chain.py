"""Document retrieval chain using ChromaDB for similarity search."""

import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from functools import lru_cache

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available. Install with: pip install chromadb")

from app.core.llm_client import get_embeddings_model
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentRetrievalService:
    """Document retrieval service using ChromaDB for semantic similarity search."""

    def __init__(
        self,
        collection_name: str = "creditnexus_documents",
        persist_directory: Optional[str] = None,
    ) -> None:
        """Initialize document retrieval service.

        Args:
            collection_name: Name of the ChromaDB collection (default: "creditnexus_documents")
            persist_directory: Directory to persist ChromaDB data (default: ./chroma_db)
        """
        if not CHROMADB_AVAILABLE:
            raise ImportError(
                "ChromaDB is not installed. Install with: pip install chromadb"
            )

        # Set default persist directory
        if persist_directory is None:
            persist_directory = getattr(settings, "CHROMADB_PERSIST_DIR", "./chroma_db")
        
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        self.embeddings_model = None
        
        # Initialize ChromaDB client and collection
        self._initialize_client()
        self._initialize_embeddings()

    def _initialize_client(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "CreditNexus document embeddings for similarity search"}
            )
            
            logger.info(
                f"Initialized ChromaDB collection '{self.collection_name}' "
                f"with {self.collection.count()} documents"
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise

    def _initialize_embeddings(self) -> None:
        """Initialize embeddings model."""
        try:
            self.embeddings_model = get_embeddings_model()
            logger.info("Initialized embeddings model for document retrieval")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings model: {e}")
            raise

    def _cdm_to_text(self, cdm_data: Dict[str, Any]) -> str:
        """Convert CDM data to searchable text representation.
        
        Args:
            cdm_data: CDM data dictionary
            
        Returns:
            Text representation of CDM data for embedding
        """
        text_parts = []
        
        # Extract parties
        if "parties" in cdm_data and isinstance(cdm_data["parties"], list):
            for party in cdm_data["parties"]:
                if isinstance(party, dict):
                    name = party.get("name", "")
                    role = party.get("role", "")
                    if name:
                        text_parts.append(f"Party: {name} ({role})")
        
        # Extract facilities
        if "facilities" in cdm_data and isinstance(cdm_data["facilities"], list):
            for facility in cdm_data["facilities"]:
                if isinstance(facility, dict):
                    facility_name = facility.get("facility_name", "")
                    commitment = facility.get("commitment_amount", {})
                    amount = commitment.get("amount", "") if isinstance(commitment, dict) else ""
                    currency = commitment.get("currency", "") if isinstance(commitment, dict) else ""
                    if facility_name:
                        text_parts.append(f"Facility: {facility_name} {amount} {currency}")
        
        # Extract agreement details
        if "agreement_date" in cdm_data:
            text_parts.append(f"Agreement Date: {cdm_data['agreement_date']}")
        
        if "governing_law" in cdm_data:
            text_parts.append(f"Governing Law: {cdm_data['governing_law']}")
        
        if "deal_id" in cdm_data:
            text_parts.append(f"Deal ID: {cdm_data['deal_id']}")
        
        # Extract ESG data
        if "sustainability_linked" in cdm_data and cdm_data["sustainability_linked"]:
            text_parts.append("Sustainability-Linked Loan")
        
        if "esg_kpi_targets" in cdm_data and isinstance(cdm_data["esg_kpi_targets"], list):
            for kpi in cdm_data["esg_kpi_targets"]:
                if isinstance(kpi, dict):
                    kpi_type = kpi.get("kpi_type", "")
                    target_value = kpi.get("target_value", "")
                    if kpi_type:
                        text_parts.append(f"ESG KPI: {kpi_type} target {target_value}")
        
        # Fallback to JSON string if no structured data
        if not text_parts:
            return json.dumps(cdm_data, default=str)
        
        return " | ".join(text_parts)
    
    def _profile_to_text(self, profile_data: Dict[str, Any]) -> str:
        """Convert user profile data to searchable text representation.
        
        Args:
            profile_data: User profile data dictionary
            
        Returns:
            Text representation of profile data for embedding
        """
        text_parts = []
        
        # Personal information
        if profile_data.get("first_name"):
            text_parts.append(f"First Name: {profile_data['first_name']}")
        if profile_data.get("last_name"):
            text_parts.append(f"Last Name: {profile_data['last_name']}")
        if profile_data.get("full_name"):
            text_parts.append(f"Full Name: {profile_data['full_name']}")
        if profile_data.get("nationality"):
            text_parts.append(f"Nationality: {profile_data['nationality']}")
        
        # Contact information
        if "contact" in profile_data and isinstance(profile_data["contact"], dict):
            contact = profile_data["contact"]
            if contact.get("email"):
                text_parts.append(f"Email: {contact['email']}")
            if contact.get("phone"):
                text_parts.append(f"Phone: {contact['phone']}")
            if contact.get("mobile"):
                text_parts.append(f"Mobile: {contact['mobile']}")
            if contact.get("linkedin"):
                text_parts.append(f"LinkedIn: {contact['linkedin']}")
        
        # Professional information
        if "professional" in profile_data and isinstance(profile_data["professional"], dict):
            prof = profile_data["professional"]
            if prof.get("job_title"):
                text_parts.append(f"Job Title: {prof['job_title']}")
            if prof.get("department"):
                text_parts.append(f"Department: {prof['department']}")
            if prof.get("certifications"):
                certs = ", ".join(prof["certifications"]) if isinstance(prof["certifications"], list) else str(prof["certifications"])
                text_parts.append(f"Certifications: {certs}")
            if prof.get("licenses"):
                licenses = ", ".join(prof["licenses"]) if isinstance(prof["licenses"], list) else str(prof["licenses"])
                text_parts.append(f"Licenses: {licenses}")
            if prof.get("specializations"):
                specs = ", ".join(prof["specializations"]) if isinstance(prof["specializations"], list) else str(prof["specializations"])
                text_parts.append(f"Specializations: {specs}")
        
        # Company information
        if "company" in profile_data and isinstance(profile_data["company"], dict):
            company = profile_data["company"]
            if company.get("name"):
                text_parts.append(f"Company: {company['name']}")
            if company.get("legal_name"):
                text_parts.append(f"Legal Name: {company['legal_name']}")
            if company.get("lei"):
                text_parts.append(f"LEI: {company['lei']}")
            if company.get("industry"):
                text_parts.append(f"Industry: {company['industry']}")
            if company.get("registration_number"):
                text_parts.append(f"Registration: {company['registration_number']}")
            if company.get("tax_id"):
                text_parts.append(f"Tax ID: {company['tax_id']}")
            if "address" in company and isinstance(company["address"], dict):
                addr = company["address"]
                addr_parts = []
                if addr.get("city"):
                    addr_parts.append(addr["city"])
                if addr.get("state"):
                    addr_parts.append(addr["state"])
                if addr.get("country"):
                    addr_parts.append(addr["country"])
                if addr_parts:
                    text_parts.append(f"Company Location: {', '.join(addr_parts)}")
        
        # Financial information
        if "financial" in profile_data and isinstance(profile_data["financial"], dict):
            financial = profile_data["financial"]
            if financial.get("annual_revenue"):
                currency = financial.get("revenue_currency", "USD")
                text_parts.append(f"Annual Revenue: {financial['annual_revenue']} {currency}")
            if financial.get("credit_rating"):
                agency = financial.get("credit_rating_agency", "")
                text_parts.append(f"Credit Rating: {financial['credit_rating']} {agency}")
        
        # Personal address
        if "personal_address" in profile_data and isinstance(profile_data["personal_address"], dict):
            addr = profile_data["personal_address"]
            if addr.get("full_address"):
                text_parts.append(f"Address: {addr['full_address']}")
            else:
                addr_parts = []
                if addr.get("city"):
                    addr_parts.append(addr["city"])
                if addr.get("state"):
                    addr_parts.append(addr["state"])
                if addr.get("country"):
                    addr_parts.append(addr["country"])
                if addr_parts:
                    text_parts.append(f"Location: {', '.join(addr_parts)}")
        
        # Role-specific data
        if "role_specific_data" in profile_data and isinstance(profile_data["role_specific_data"], dict):
            for key, value in profile_data["role_specific_data"].items():
                if value:
                    text_parts.append(f"{key}: {value}")
        
        # Fallback to JSON string if no structured data
        if not text_parts:
            return json.dumps(profile_data, default=str)
        
        return " | ".join(text_parts)

    def add_document(
        self,
        document_id: int,
        cdm_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add or update a document in the vector store.
        
        Args:
            document_id: Document ID from database
            cdm_data: CDM data dictionary to index
            metadata: Additional metadata (title, borrower_name, etc.)
        """
        try:
            # Convert CDM data to text
            text = self._cdm_to_text(cdm_data)
            
            # Generate embedding
            embedding = self.embeddings_model.embed_query(text)
            
            # Prepare metadata
            doc_metadata = {
                "document_id": str(document_id),
                "text": text[:1000],  # Store first 1000 chars for reference
            }
            
            if metadata:
                # Add metadata fields (convert to strings for ChromaDB)
                for key, value in metadata.items():
                    if value is not None:
                        doc_metadata[key] = str(value)
            
            # Add or update document in collection
            # Use document_id as the unique ID
            self.collection.upsert(
                ids=[str(document_id)],
                embeddings=[embedding],
                documents=[text],
                metadatas=[doc_metadata]
            )
            
            logger.info(f"Indexed document {document_id} in ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to add document {document_id} to vector store: {e}")
            raise

    def retrieve_similar_documents(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve similar documents based on query text or CDM data.
        
        Args:
            query: Query text or CDM data (will be converted to text if dict)
            top_k: Number of similar documents to retrieve (default: 5)
            filter_metadata: Optional metadata filters (e.g., {"borrower_name": "ACME Corp"})
            
        Returns:
            List of similar documents with scores, CDM data, and metadata
        """
        try:
            # Convert query to text if it's a dict (CDM data)
            if isinstance(query, dict):
                query_text = self._cdm_to_text(query)
            else:
                query_text = str(query)
            
            # Generate query embedding
            query_embedding = self.embeddings_model.embed_query(query_text)
            
            # Prepare where clause for filtering
            where = None
            if filter_metadata:
                where = {k: str(v) for k, v in filter_metadata.items()}
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            similar_docs = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for idx in range(len(results["ids"][0])):
                    doc_id = results["ids"][0][idx]
                    distance = results["distances"][0][idx]
                    metadata = results["metadatas"][0][idx] if results["metadatas"] else {}
                    document_text = results["documents"][0][idx] if results["documents"] else ""
                    
                    # Convert distance to similarity score (1 - distance for cosine similarity)
                    similarity_score = 1.0 - distance if distance <= 1.0 else 0.0
                    
                    similar_docs.append({
                        "document_id": int(metadata.get("document_id", doc_id)),
                        "similarity_score": similarity_score,
                        "distance": distance,
                        "metadata": metadata,
                        "document_text": document_text,
                    })
            
            logger.info(
                f"Retrieved {len(similar_docs)} similar documents for query: {query_text[:50]}..."
            )
            
            return similar_docs
            
        except Exception as e:
            logger.error(f"Failed to retrieve similar documents: {e}")
            raise

    def delete_document(self, document_id: int) -> None:
        """Delete a document from the vector store.
        
        Args:
            document_id: Document ID to delete
        """
        try:
            self.collection.delete(ids=[str(document_id)])
            logger.info(f"Deleted document {document_id} from ChromaDB")
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get statistics about the collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                "collection_name": self.collection_name,
                "document_count": count,
                "persist_directory": str(self.persist_directory),
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {
                "collection_name": self.collection_name,
                "document_count": 0,
                "error": str(e),
            }


@lru_cache(maxsize=1)
def get_document_retrieval_service() -> DocumentRetrievalService:
    """Get or create singleton document retrieval service instance.

    Returns:
        DocumentRetrievalService instance
    """
    return DocumentRetrievalService()


def create_document_retrieval_chain() -> DocumentRetrievalService:
    """Create document retrieval chain instance.

    Returns:
        DocumentRetrievalService instance
    """
    return get_document_retrieval_service()


def retrieve_similar_documents(
    query: str,
    top_k: int = 5,
    filter_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Retrieve similar documents based on query.

    Convenience function that creates a retrieval service and searches.

    Args:
        query: Query text or CDM data dictionary
        top_k: Number of similar documents to retrieve (default: 5)
        filter_metadata: Optional metadata filters

    Returns:
        List of similar documents with scores and metadata

    Raises:
        ImportError: If ChromaDB is not installed
    """
    service = get_document_retrieval_service()
    return service.retrieve_similar_documents(
        query=query,
        top_k=top_k,
        filter_metadata=filter_metadata,
    )


# User Profile Collection Service
def get_user_profile_retrieval_service() -> DocumentRetrievalService:
    """Get or create singleton user profile retrieval service instance.

    Returns:
        DocumentRetrievalService instance configured for user_profiles collection
    """
    return DocumentRetrievalService(collection_name="creditnexus_user_profiles")


def add_user_profile(
    user_id: int,
    profile_data: Dict[str, Any],
    role: Optional[str] = None,
    email: Optional[str] = None,
) -> None:
    """Add or update a user profile in ChromaDB.

    Args:
        user_id: User ID from database
        profile_data: User profile data dictionary (from UserProfileData model)
        role: Optional user role
        email: Optional user email
    """
    try:
        service = get_user_profile_retrieval_service()
        
        # Convert profile data to text
        text = service._profile_to_text(profile_data)
        
        # Generate embedding
        embedding = service.embeddings_model.embed_query(text)
        
        # Prepare metadata
        metadata = {
            "user_id": str(user_id),
            "text": text[:1000],  # Store first 1000 chars for reference
        }
        
        if role:
            metadata["role"] = str(role)
        if email:
            metadata["email"] = str(email)
        
        # Add company name if available
        if "company" in profile_data and isinstance(profile_data["company"], dict):
            if profile_data["company"].get("name"):
                metadata["company_name"] = str(profile_data["company"]["name"])
            if profile_data["company"].get("lei"):
                metadata["company_lei"] = str(profile_data["company"]["lei"])
        
        # Add full name if available
        if profile_data.get("full_name"):
            metadata["full_name"] = str(profile_data["full_name"])
        elif profile_data.get("first_name") or profile_data.get("last_name"):
            name_parts = []
            if profile_data.get("first_name"):
                name_parts.append(profile_data["first_name"])
            if profile_data.get("last_name"):
                name_parts.append(profile_data["last_name"])
            if name_parts:
                metadata["full_name"] = " ".join(name_parts)
        
        # Add or update profile in collection
        service.collection.upsert(
            ids=[str(user_id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
        
        logger.info(f"Indexed user profile {user_id} in ChromaDB")
        
    except Exception as e:
        logger.error(f"Failed to add user profile {user_id} to vector store: {e}")
        raise


def search_user_profiles(
    query: str,
    top_k: int = 10,
    filter_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search for user profiles based on query.

    Args:
        query: Query text or profile data dictionary
        top_k: Number of similar profiles to retrieve (default: 10)
        filter_metadata: Optional metadata filters (e.g., {"role": "banker", "company_name": "ACME"})

    Returns:
        List of similar user profiles with scores and metadata
    """
    try:
        service = get_user_profile_retrieval_service()
        
        # Convert query to text if it's a dict (profile data)
        if isinstance(query, dict):
            query_text = service._profile_to_text(query)
        else:
            query_text = str(query)
        
        # Generate query embedding
        query_embedding = service.embeddings_model.embed_query(query_text)
        
        # Prepare where clause for filtering
        where = None
        if filter_metadata:
            where = {k: str(v) for k, v in filter_metadata.items()}
        
        # Search in ChromaDB
        results = service.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        similar_profiles = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for idx in range(len(results["ids"][0])):
                profile_id = results["ids"][0][idx]
                distance = results["distances"][0][idx]
                metadata = results["metadatas"][0][idx] if results["metadatas"] else {}
                profile_text = results["documents"][0][idx] if results["documents"] else ""
                
                # Convert distance to similarity score (1 - distance for cosine similarity)
                similarity_score = 1.0 - distance if distance <= 1.0 else 0.0
                
                similar_profiles.append({
                    "user_id": int(metadata.get("user_id", profile_id)),
                    "similarity_score": similarity_score,
                    "distance": distance,
                    "metadata": metadata,
                    "profile_text": profile_text,
                })
        
        logger.info(
            f"Retrieved {len(similar_profiles)} similar user profiles for query: {query_text[:50]}..."
        )
        
        return similar_profiles
        
    except Exception as e:
        logger.error(f"Failed to search user profiles: {e}")
        raise


def delete_user_profile(user_id: int) -> None:
    """Delete a user profile from ChromaDB.

    Args:
        user_id: User ID to delete
    """
    try:
        service = get_user_profile_retrieval_service()
        service.collection.delete(ids=[str(user_id)])
        logger.info(f"Deleted user profile {user_id} from ChromaDB")
    except Exception as e:
        logger.error(f"Failed to delete user profile {user_id}: {e}")
        raise


# Deal Collection Service
def get_deal_retrieval_service() -> DocumentRetrievalService:
    """Get or create singleton deal retrieval service instance.

    Returns:
        DocumentRetrievalService instance configured for deals collection
    """
    return DocumentRetrievalService(collection_name="creditnexus_deals")


def _deal_to_text(deal_data: Dict[str, Any]) -> str:
    """Convert deal data to searchable text representation.
    
    Args:
        deal_data: Deal data dictionary with deal_id, status, deal_type, deal_data, etc.
        
    Returns:
        Text representation of deal data for embedding
    """
    text_parts = []
    
    # Deal ID
    if deal_data.get("deal_id"):
        text_parts.append(f"Deal ID: {deal_data['deal_id']}")
    
    # Deal type
    if deal_data.get("deal_type"):
        text_parts.append(f"Deal Type: {deal_data['deal_type']}")
    
    # Deal status
    if deal_data.get("status"):
        text_parts.append(f"Status: {deal_data['status']}")
    
    # Deal data (nested structure)
    if deal_data.get("deal_data") and isinstance(deal_data["deal_data"], dict):
        deal_data_dict = deal_data["deal_data"]
        
        # Extract borrower/applicant information
        if deal_data_dict.get("borrower_name"):
            text_parts.append(f"Borrower: {deal_data_dict['borrower_name']}")
        if deal_data_dict.get("applicant_name"):
            text_parts.append(f"Applicant: {deal_data_dict['applicant_name']}")
        
        # Extract loan/facility information
        if deal_data_dict.get("loan_amount"):
            text_parts.append(f"Loan Amount: {deal_data_dict['loan_amount']}")
        if deal_data_dict.get("facility_type"):
            text_parts.append(f"Facility Type: {deal_data_dict['facility_type']}")
        if deal_data_dict.get("purpose"):
            text_parts.append(f"Purpose: {deal_data_dict['purpose']}")
        
        # Extract dates
        if deal_data_dict.get("application_date"):
            text_parts.append(f"Application Date: {deal_data_dict['application_date']}")
        if deal_data_dict.get("expected_closing_date"):
            text_parts.append(f"Expected Closing: {deal_data_dict['expected_closing_date']}")
        
        # Extract other relevant fields
        for key, value in deal_data_dict.items():
            if key not in ["borrower_name", "applicant_name", "loan_amount", "facility_type", 
                          "purpose", "application_date", "expected_closing_date"]:
                if value and isinstance(value, (str, int, float)):
                    text_parts.append(f"{key}: {value}")
    
    # Documents summary (if provided)
    if deal_data.get("documents") and isinstance(deal_data["documents"], list):
        doc_count = len(deal_data["documents"])
        text_parts.append(f"Documents: {doc_count} document(s)")
        # Include document titles if available
        for doc in deal_data["documents"][:3]:  # First 3 documents
            if isinstance(doc, dict):
                title = doc.get("title") or doc.get("filename", "")
                if title:
                    text_parts.append(f"Document: {title}")
    
    # Notes summary (if provided)
    if deal_data.get("notes") and isinstance(deal_data["notes"], list):
        note_count = len(deal_data["notes"])
        text_parts.append(f"Notes: {note_count} note(s)")
        # Include recent note content
        for note in deal_data["notes"][:2]:  # First 2 notes
            if isinstance(note, dict):
                content = note.get("content", "")
                note_type = note.get("note_type", "")
                if content:
                    # Truncate long notes
                    content_preview = content[:200] + "..." if len(content) > 200 else content
                    text_parts.append(f"Note ({note_type}): {content_preview}")
    
    # Fallback to JSON string if no structured data
    if not text_parts:
        return json.dumps(deal_data, default=str)
    
    return " | ".join(text_parts)


def add_deal(
    deal_id: int,
    deal_data: Dict[str, Any],
    documents: Optional[List[Dict[str, Any]]] = None,
    notes: Optional[List[Dict[str, Any]]] = None,
) -> None:
    """Add or update a deal in ChromaDB.

    Args:
        deal_id: Deal ID from database
        deal_data: Deal data dictionary with deal_id, status, deal_type, deal_data, etc.
        documents: Optional list of document metadata attached to the deal
        notes: Optional list of note metadata attached to the deal
    """
    try:
        service = get_deal_retrieval_service()
        
        # Prepare full deal data with documents and notes
        full_deal_data = deal_data.copy()
        if documents:
            full_deal_data["documents"] = documents
        if notes:
            full_deal_data["notes"] = notes
        
        # Convert deal data to text
        text = _deal_to_text(full_deal_data)
        
        # Generate embedding
        embedding = service.embeddings_model.embed_query(text)
        
        # Prepare metadata
        metadata = {
            "deal_id": str(deal_id),
            "text": text[:1000],  # Store first 1000 chars for reference
        }
        
        if deal_data.get("deal_id"):
            metadata["deal_deal_id"] = str(deal_data["deal_id"])
        if deal_data.get("status"):
            metadata["status"] = str(deal_data["status"])
        if deal_data.get("deal_type"):
            metadata["deal_type"] = str(deal_data["deal_type"])
        if deal_data.get("applicant_id"):
            metadata["applicant_id"] = str(deal_data["applicant_id"])
        
        # Add document count
        if documents:
            metadata["document_count"] = str(len(documents))
        
        # Add note count
        if notes:
            metadata["note_count"] = str(len(notes))
        
        # Add or update deal in collection
        service.collection.upsert(
            ids=[str(deal_id)],
            embeddings=[embedding],
            documents=[text],
            metadatas=[metadata]
        )
        
        logger.info(f"Indexed deal {deal_id} in ChromaDB")
        
    except Exception as e:
        logger.error(f"Failed to add deal {deal_id} to vector store: {e}")
        raise


def search_deals(
    query: str,
    top_k: int = 10,
    filter_metadata: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search for deals based on query.

    Args:
        query: Query text or deal data dictionary
        top_k: Number of similar deals to retrieve (default: 10)
        filter_metadata: Optional metadata filters (e.g., {"status": "active", "deal_type": "term_loan"})

    Returns:
        List of similar deals with scores and metadata
    """
    try:
        service = get_deal_retrieval_service()
        
        # Convert query to text if it's a dict (deal data)
        if isinstance(query, dict):
            query_text = _deal_to_text(query)
        else:
            query_text = str(query)
        
        # Generate query embedding
        query_embedding = service.embeddings_model.embed_query(query_text)
        
        # Prepare where clause for filtering
        where = None
        if filter_metadata:
            where = {k: str(v) for k, v in filter_metadata.items()}
        
        # Search in ChromaDB
        results = service.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format results
        similar_deals = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for idx in range(len(results["ids"][0])):
                deal_id_str = results["ids"][0][idx]
                distance = results["distances"][0][idx]
                metadata = results["metadatas"][0][idx] if results["metadatas"] else {}
                deal_text = results["documents"][0][idx] if results["documents"] else ""
                
                # Convert distance to similarity score (1 - distance for cosine similarity)
                similarity_score = 1.0 - distance if distance <= 1.0 else 0.0
                
                similar_deals.append({
                    "deal_id": int(metadata.get("deal_id", deal_id_str)),
                    "similarity_score": similarity_score,
                    "distance": distance,
                    "metadata": metadata,
                    "deal_text": deal_text,
                })
        
        logger.info(
            f"Retrieved {len(similar_deals)} similar deals for query: {query_text[:50]}..."
        )
        
        return similar_deals
        
    except Exception as e:
        logger.error(f"Failed to search deals: {e}")
        raise


def delete_deal(deal_id: int) -> None:
    """Delete a deal from ChromaDB.

    Args:
        deal_id: Deal ID to delete
    """
    try:
        service = get_deal_retrieval_service()
        service.collection.delete(ids=[str(deal_id)])
        logger.info(f"Deleted deal {deal_id} from ChromaDB")
    except Exception as e:
        logger.error(f"Failed to delete deal {deal_id}: {e}")
        raise















