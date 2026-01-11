"""Decision support chatbot chain for LMA template generation.

This module implements an AI chatbot that provides decision support for:
- Template selection based on CDM data
- Interactive field filling
- General questions about LMA templates and CDM schema
- Uses RAG (Retrieval Augmented Generation) with ChromaDB knowledge base
"""

import logging
import json
from typing import List, Dict, Any, Optional, TYPE_CHECKING
from pathlib import Path

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    logging.warning("ChromaDB not available. Install with: pip install chromadb")

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from app.core.llm_client import get_chat_model, get_embeddings_model
from app.core.config import settings

logger = logging.getLogger(__name__)


class DecisionSupportChatbot:
    """AI chatbot for decision support in LMA template generation.
    
    Provides:
    - Chat interface with CDM context
    - Template suggestions based on CDM data
    - Interactive field filling assistance
    - Knowledge base retrieval for templates and CDM schema
    """
    
    def __init__(
        self,
        kb_collection_name: str = "chatbot_knowledge_base",
        persist_directory: Optional[str] = None,
        db_session: Optional['Session'] = None,
    ):
        """Initialize decision support chatbot.
        
        Args:
            kb_collection_name: Name of ChromaDB collection for knowledge base
            persist_directory: Directory to persist ChromaDB data
            db_session: Optional database session for loading deal/user context
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
        
        self.kb_collection_name = kb_collection_name
        self.db_session = db_session
        self.client = None
        self.collection = None
        self.embeddings_model = None
        self.llm = None
        
        # Initialize ChromaDB and models
        self._initialize_client()
        self._initialize_models()
    
    def _initialize_client(self) -> None:
        """Initialize ChromaDB client and collection."""
        try:
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=self.kb_collection_name,
                metadata={"description": "Chatbot knowledge base for LMA templates and CDM schema"}
            )
            
            logger.info(
                f"Initialized ChromaDB collection '{self.kb_collection_name}' "
                f"with {self.collection.count()} documents"
            )
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB client: {e}")
            raise
    
    def _initialize_models(self) -> None:
        """Initialize LLM and embeddings models."""
        try:
            self.embeddings_model = get_embeddings_model()
            self.llm = get_chat_model(temperature=0.7)  # Higher temperature for conversational responses
            logger.info("Initialized LLM and embeddings models for chatbot")
        except Exception as e:
            logger.error(f"Failed to initialize models: {e}")
            raise
    
    def _retrieve_relevant_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve relevant context from knowledge base.
        
        Args:
            query: User query
            top_k: Number of relevant documents to retrieve
            
        Returns:
            List of relevant documents with metadata
        """
        try:
            if self.collection.count() == 0:
                return []
            
            # Generate query embedding
            query_embedding = self.embeddings_model.embed_query(query)
            
            # Search in ChromaDB
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            contexts = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for idx in range(len(results["ids"][0])):
                    contexts.append({
                        "content": results["documents"][0][idx],
                        "metadata": results["metadatas"][0][idx] if results["metadatas"] else {},
                        "distance": results["distances"][0][idx] if results["distances"] else None,
                    })
            
            return contexts
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return []
    
    def _load_deal_context(
        self,
        deal_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Load deal context including deal metadata, documents, and user profile.
        
        Args:
            deal_id: Optional deal ID to load context for
            user_id: Optional user ID to load profile for
            
        Returns:
            Dictionary with deal context, documents, and user profile
        """
        context = {
            "deal": None,
            "deal_documents": [],
            "user_profile": None,
            "deal_notes": [],
        }
        
        if not self.db_session:
            return context
        
        try:
            # Load deal information
            if deal_id:
                from app.services.deal_service import DealService
                from app.chains.document_retrieval_chain import DocumentRetrievalService
                
                deal_service = DealService(self.db_session)
                deal = deal_service.get_deal(deal_id)
                
                if deal:
                    context["deal"] = {
                        "deal_id": deal.deal_id,
                        "status": deal.status,
                        "deal_type": deal.deal_type,
                        "deal_data": deal.deal_data,
                        "created_at": deal.created_at.isoformat() if deal.created_at else None,
                    }
                    
                    # Load deal documents from database, file storage, and ChromaDB
                    try:
                        from app.db.models import Document
                        from app.services.file_storage_service import FileStorageService
                        from app.chains.document_retrieval_chain import DocumentRetrievalService
                        
                        # Get documents from database
                        db_docs = self.db_session.query(Document).filter(
                            Document.deal_id == deal_id
                        ).order_by(Document.created_at.desc()).limit(10).all()
                        
                        # Query ChromaDB for semantically similar deal documents
                        chroma_docs = []
                        try:
                            doc_retrieval = DocumentRetrievalService(collection_name="creditnexus_documents")
                            # Create a search query from deal metadata
                            search_query = f"deal {deal.deal_id} {deal.deal_type or ''} {deal.status or ''}"
                            if deal.deal_data:
                                # Extract key terms from deal_data for search
                                if isinstance(deal.deal_data, dict):
                                    search_terms = []
                                    for key, value in list(deal.deal_data.items())[:5]:  # First 5 fields
                                        if value and isinstance(value, (str, int, float)):
                                            search_terms.append(str(value))
                                    if search_terms:
                                        search_query += " " + " ".join(search_terms)
                            
                            # Search for similar documents
                            similar_docs = doc_retrieval.retrieve_similar_documents(
                                query=search_query,
                                top_k=5,
                                filter_metadata={"deal_id": str(deal_id)} if deal_id else None
                            )
                            chroma_docs = similar_docs
                        except Exception as e:
                            logger.warning(f"Failed to query ChromaDB for deal documents: {e}")
                        
                        # Get documents from file storage
                        file_storage = FileStorageService()
                        file_docs = []
                        if deal.applicant_id and deal.deal_id:
                            file_docs = file_storage.get_deal_documents(
                                user_id=deal.applicant_id,
                                deal_id=deal.deal_id
                            )
                        
                        # Combine all document sources
                        all_docs = []
                        # Add database documents
                        for doc in db_docs:
                            all_docs.append({
                                "document_id": doc.id,
                                "title": doc.title,
                                "filename": doc.title,
                                "subdirectory": "documents",
                                "source": "database",
                                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                            })
                        # Add ChromaDB documents (semantic search results)
                        for doc in chroma_docs:
                            all_docs.append({
                                "document_id": doc.get("document_id"),
                                "title": doc.get("title", "Document"),
                                "filename": doc.get("title", "Document"),
                                "subdirectory": "documents",
                                "source": "chromadb",
                                "similarity": doc.get("similarity"),
                            })
                        # Add file storage documents
                        for doc in file_docs[:5]:  # Limit file storage docs
                            all_docs.append({
                                "filename": doc.get("filename", "Unknown"),
                                "subdirectory": doc.get("subdirectory", "documents"),
                                "source": "file_storage",
                                "size": doc.get("size"),
                                "modified_at": doc.get("modified_at"),
                            })
                        
                        context["deal_documents"] = all_docs[:15]  # Limit to 15 total
                    except Exception as e:
                        logger.warning(f"Failed to load deal documents: {e}")
                    
                    # Load deal notes
                    try:
                        from app.db.models import DealNote
                        notes = self.db_session.query(DealNote).filter(
                            DealNote.deal_id == deal_id
                        ).order_by(DealNote.created_at.desc()).limit(5).all()
                        
                        context["deal_notes"] = [
                            {
                                "id": note.id,
                                "content": note.content[:200],  # First 200 chars
                                "note_type": note.note_type,
                                "created_at": note.created_at.isoformat() if note.created_at else None,
                            }
                            for note in notes
                        ]
                    except Exception as e:
                        logger.warning(f"Failed to load deal notes: {e}")
            
            # Load user profile from database and ChromaDB
            if user_id:
                try:
                    from app.db.models import User
                    from app.chains.document_retrieval_chain import get_user_profile_retrieval_service
                    
                    # Get user from database
                    user = self.db_session.query(User).filter(User.id == user_id).first()
                    if user:
                        profile_data = {
                            "role": user.role,
                            "display_name": user.display_name,
                            "email": user.email,
                            "profile_data": user.profile_data,
                        }
                        
                        # Query ChromaDB for semantically similar user profiles
                        try:
                            profile_retrieval = get_user_profile_retrieval_service()
                            if user.profile_data:
                                # Create search query from profile data
                                search_query = f"{user.display_name} {user.role}"
                                if isinstance(user.profile_data, dict):
                                    if user.profile_data.get("company", {}).get("name"):
                                        search_query += f" {user.profile_data['company']['name']}"
                                    if user.profile_data.get("professional", {}).get("job_title"):
                                        search_query += f" {user.profile_data['professional']['job_title']}"
                                
                                # Search for similar profiles
                                similar_profiles = profile_retrieval.search_user_profiles(
                                    query=search_query,
                                    top_k=3
                                )
                                
                                if similar_profiles:
                                    profile_data["similar_profiles"] = [
                                        {
                                            "user_id": p.get("user_id"),
                                            "similarity_score": p.get("similarity_score"),
                                            "profile_text": p.get("profile_text", "")[:200],
                                            "metadata": p.get("metadata", {}),
                                        }
                                        for p in similar_profiles
                                    ]
                        except Exception as e:
                            logger.warning(f"Failed to query ChromaDB for user profiles: {e}")
                        
                        context["user_profile"] = profile_data
                except Exception as e:
                    logger.warning(f"Failed to load user profile: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load deal context: {e}", exc_info=True)
        
        return context
    
    def chat(
        self,
        message: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        cdm_context: Optional[Dict[str, Any]] = None,
        use_kb: bool = True,
        deal_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Chat with the decision support chatbot.
        
        Args:
            message: User message
            conversation_history: Previous conversation messages [{"role": "user"|"assistant", "content": "..."}]
            cdm_context: Current CDM data context
            use_kb: Whether to use knowledge base retrieval
            deal_id: Optional deal ID to load deal context
            user_id: Optional user ID to load user profile
            
        Returns:
            Dictionary with response and metadata
        """
        try:
            # Load deal context if deal_id provided
            deal_context = self._load_deal_context(deal_id=deal_id, user_id=user_id)
            
            # Retrieve relevant context from knowledge base
            context_docs = []
            if use_kb:
                context_docs = self._retrieve_relevant_context(message, top_k=5)
            
            # Build system prompt with deal context
            system_prompt = """You are an expert AI assistant for LMA (Loan Market Association) document generation.
Your role is to help users:
1. Select appropriate LMA templates based on their credit agreement data (CDM) and deal type
2. Fill missing CDM fields interactively
3. Answer questions about LMA templates, CDM schema, and document generation
4. Provide guidance on best practices for credit agreement documentation
5. Provide context-aware assistance based on the current deal and user profile
6. Recommend templates based on deal type and explain why they are needed
7. Help users understand which templates are required vs optional for their deal

You have access to a knowledge base of LMA template metadata and CDM schema documentation.
Use this knowledge to provide accurate, helpful responses.

Be conversational, helpful, and precise. When suggesting templates, explain why they match the user's needs.
When helping fill fields, ask clarifying questions if needed.
When deal context is available, use it to provide more relevant and specific assistance.

IMPORTANT CONTEXT AWARENESS:
- If deal context is provided, reference the deal ID, status, and type in your responses
- Use information from attached documents to answer questions
- Consider the user's role and permissions when providing guidance
- Reference deal notes and recent activity when relevant
- If template recommendations are provided, prioritize suggesting missing required templates
- Explain why each recommended template is needed for the deal type
- Help users understand the completion status of their template generation"""
            
            # Build context from knowledge base
            kb_context = ""
            if context_docs:
                kb_context = "\n\nRelevant Knowledge Base Information:\n"
                for doc in context_docs:
                    kb_context += f"- {doc['content']}\n"
                    if doc.get('metadata', {}).get('source'):
                        kb_context += f"  (Source: {doc['metadata']['source']})\n"
            
            # Load template recommendations if deal_id provided
            template_recommendations_str = ""
            if deal_id and self.db_session:
                try:
                    from app.services.template_recommendation_service import TemplateRecommendationService
                    recommendation_service = TemplateRecommendationService(self.db_session)
                    recommendations = recommendation_service.recommend_templates(deal_id)
                    
                    if recommendations and not recommendations.get("error"):
                        template_recommendations_str = "\n\nTemplate Recommendations:\n"
                        
                        # Missing required templates
                        if recommendations.get("missing_required"):
                            template_recommendations_str += f"\nMissing Required Templates ({len(recommendations['missing_required'])}):\n"
                            for template in recommendations["missing_required"][:5]:  # Show first 5
                                template_recommendations_str += f"- {template.get('name')} ({template.get('category')})\n"
                                template_recommendations_str += f"  Reason: {template.get('reason')}\n"
                                template_recommendations_str += f"  Template ID: {template.get('template_id')}\n"
                        
                        # Optional templates
                        if recommendations.get("optional_not_generated"):
                            template_recommendations_str += f"\nRecommended Optional Templates ({len(recommendations['optional_not_generated'])}):\n"
                            for template in recommendations["optional_not_generated"][:3]:  # Show first 3
                                template_recommendations_str += f"- {template.get('name')} ({template.get('category')}) - Priority: {template.get('priority')}\n"
                                template_recommendations_str += f"  Reason: {template.get('reason')}\n"
                        
                        # Generated templates
                        if recommendations.get("generated_templates"):
                            template_recommendations_str += f"\nAlready Generated Templates ({len(recommendations['generated_templates'])}):\n"
                            for template in recommendations["generated_templates"][:5]:  # Show first 5
                                template_recommendations_str += f"- {template.get('name')} ({template.get('category')})\n"
                        
                        # Completion status
                        completion = recommendations.get("completion_status", {})
                        if completion:
                            template_recommendations_str += f"\nTemplate Completion: {completion.get('required_generated', 0)}/{completion.get('required_total', 0)} required templates generated ({completion.get('completion_percentage', 0):.1f}%)\n"
                except Exception as e:
                    logger.warning(f"Failed to load template recommendations: {e}")
            
            # Build deal context string
            deal_context_str = ""
            if deal_context.get("deal"):
                deal = deal_context["deal"]
                deal_context_str = f"\n\nCurrent Deal Context:\n"
                deal_context_str += f"Deal ID: {deal.get('deal_id')}\n"
                deal_context_str += f"Status: {deal.get('status')}\n"
                deal_context_str += f"Type: {deal.get('deal_type')}\n"
                if deal.get('deal_data'):
                    deal_context_str += f"Deal Data: {json.dumps(deal['deal_data'], indent=2, default=str)}\n"
                
                if deal_context.get("deal_documents"):
                    deal_context_str += f"\nAttached Documents ({len(deal_context['deal_documents'])}):\n"
                    for doc in deal_context["deal_documents"][:5]:  # Show first 5
                        deal_context_str += f"- {doc.get('filename', 'Unknown')} ({doc.get('subdirectory', 'documents')})\n"
                
                if deal_context.get("deal_notes"):
                    deal_context_str += f"\nRecent Notes ({len(deal_context['deal_notes'])}):\n"
                    for note in deal_context["deal_notes"][:3]:  # Show first 3
                        deal_context_str += f"- [{note.get('note_type', 'note')}] {note.get('content', '')}\n"
            
            # Build user profile context
            user_context_str = ""
            if deal_context.get("user_profile"):
                profile = deal_context["user_profile"]
                user_context_str = f"\n\nUser Profile Context:\n"
                user_context_str += f"Role: {profile.get('role')}\n"
                user_context_str += f"Name: {profile.get('display_name')}\n"
                if profile.get('profile_data'):
                    user_context_str += f"Profile: {json.dumps(profile['profile_data'], indent=2, default=str)}\n"
            
            # Build CDM context
            cdm_context_str = ""
            if cdm_context:
                cdm_context_str = f"\n\nCurrent CDM Data Context:\n{json.dumps(cdm_context, indent=2, default=str)}"
            
            # Build conversation history
            messages = [SystemMessage(content=system_prompt + kb_context + deal_context_str + template_recommendations_str + user_context_str + cdm_context_str)]
            
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        messages.append(AIMessage(content=msg["content"]))
            
            # Add current user message
            messages.append(HumanMessage(content=message))
            
            # Generate response
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            return {
                "response": response_text,
                "sources": [doc.get('metadata', {}).get('source', 'knowledge_base') for doc in context_docs],
                "context_used": len(context_docs) > 0,
                "deal_context_loaded": deal_context.get("deal") is not None,
                "user_profile_loaded": deal_context.get("user_profile") is not None,
            }
        except Exception as e:
            logger.error(f"Chat failed: {e}", exc_info=True)
            return {
                "response": f"I apologize, but I encountered an error: {str(e)}",
                "sources": [],
                "context_used": False,
                "error": str(e),
            }
    
    def suggest_template(
        self,
        cdm_data: Dict[str, Any],
        available_templates: Optional[List[Dict[str, Any]]] = None,
        deal_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Suggest appropriate LMA templates based on CDM data and deal type.
        
        Args:
            cdm_data: CDM data dictionary
            available_templates: Optional list of available templates with metadata
            deal_id: Optional deal ID to get template recommendations based on deal type
            
        Returns:
            Dictionary with template suggestions and reasoning
        """
        try:
            # Load template recommendations if deal_id provided
            template_recommendations = None
            if deal_id and self.db_session:
                try:
                    from app.services.template_recommendation_service import TemplateRecommendationService
                    recommendation_service = TemplateRecommendationService(self.db_session)
                    template_recommendations = recommendation_service.recommend_templates(deal_id)
                except Exception as e:
                    logger.warning(f"Failed to load template recommendations: {e}")
            
            # Convert CDM data to text for context
            cdm_text = self._cdm_to_text(cdm_data)
            
            # Retrieve relevant template information from knowledge base
            template_context = self._retrieve_relevant_context(
                f"LMA template for {cdm_text}",
                top_k=10
            )
            
            # Build prompt with template recommendations if available
            system_prompt = """You are an expert LMA template selection advisor.
Analyze the provided CDM data and suggest the most appropriate LMA template(s).

Consider:
- Agreement type (facility agreement, term sheet, confidentiality agreement, etc.)
- Governing law requirements
- Sustainability-linked loan indicators
- Complexity and specific clauses needed
- Deal type and required templates (if template recommendations are provided)

Provide:
1. Primary template recommendation with reasoning
2. Alternative templates if applicable
3. Explanation of why each template fits the CDM data
4. If template recommendations are provided, prioritize missing required templates"""
            
            recommendations_context = ""
            if template_recommendations and not template_recommendations.get("error"):
                recommendations_context = f"""

Template Recommendations for Deal Type ({template_recommendations.get('deal_type', 'unknown')}):
- Missing Required Templates: {len(template_recommendations.get('missing_required', []))}
- Optional Templates Available: {len(template_recommendations.get('optional_not_generated', []))}
- Already Generated: {len(template_recommendations.get('generated_templates', []))}
- Completion: {template_recommendations.get('completion_status', {}).get('completion_percentage', 0):.1f}%

Missing Required Templates:
{json.dumps([{'name': t.get('name'), 'category': t.get('category'), 'reason': t.get('reason')} for t in template_recommendations.get('missing_required', [])[:5]], indent=2, default=str)}

Optional Templates:
{json.dumps([{'name': t.get('name'), 'category': t.get('category'), 'priority': t.get('priority'), 'reason': t.get('reason')} for t in template_recommendations.get('optional_not_generated', [])[:3]], indent=2, default=str)}
"""
            
            user_prompt = f"""CDM Data:
{cdm_text}

Available Templates:
{json.dumps(available_templates, indent=2, default=str) if available_templates else 'All templates available'}

Template Knowledge Base Context:
{chr(10).join([doc['content'] for doc in template_context[:5]]) if template_context else 'No specific template context available'}
{recommendations_context}

Suggest the most appropriate template(s) and explain your reasoning. If template recommendations are provided, prioritize the missing required templates."""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract structured suggestions
            suggestions = self._parse_template_suggestions(response_text, available_templates)
            
            return {
                "suggestions": suggestions,
                "reasoning": response_text,
                "cdm_analysis": {
                    "has_parties": bool(cdm_data.get("parties")),
                    "has_facilities": bool(cdm_data.get("facilities")),
                    "is_sustainability_linked": cdm_data.get("sustainability_linked", False),
                    "governing_law": cdm_data.get("governing_law"),
                },
            }
        except Exception as e:
            logger.error(f"Template suggestion failed: {e}", exc_info=True)
            return {
                "suggestions": [],
                "reasoning": f"Error generating suggestions: {str(e)}",
                "error": str(e),
            }
    
    def fill_missing_fields(
        self,
        cdm_data: Dict[str, Any],
        required_fields: List[str],
        conversation_context: Optional[str] = None,
        deal_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Help fill missing CDM fields interactively.
        
        Args:
            cdm_data: Current CDM data (may be incomplete)
            required_fields: List of required field paths (e.g., ["parties", "facilities[0].facility_name"])
            conversation_context: Optional conversation context about what user is trying to do
            deal_id: Optional deal ID to provide deal context for field filling
            
        Returns:
            Dictionary with field suggestions, questions, and filled data
        """
        try:
            # Load deal context if deal_id provided
            deal_context_str = ""
            if deal_id and self.db_session:
                try:
                    deal_context = self._load_deal_context(deal_id=deal_id)
                    if deal_context.get("deal"):
                        deal = deal_context["deal"]
                        deal_context_str = f"\n\nDeal Context:\n"
                        deal_context_str += f"Deal Type: {deal.get('deal_type')}\n"
                        deal_context_str += f"Deal Status: {deal.get('status')}\n"
                        if deal.get('deal_data'):
                            deal_context_str += f"Deal Data: {json.dumps(deal['deal_data'], indent=2, default=str)}\n"
                except Exception as e:
                    logger.warning(f"Failed to load deal context for field filling: {e}")
            
            # Identify missing fields
            missing_fields = self._identify_missing_fields(cdm_data, required_fields)
            
            if not missing_fields:
                return {
                    "all_fields_present": True,
                    "filled_data": cdm_data,
                    "suggestions": {},
                    "questions": [],
                }
            
            # Retrieve relevant CDM schema information
            schema_context = self._retrieve_relevant_context(
                f"CDM schema for fields: {', '.join(missing_fields)}",
                top_k=5
            )
            
            # Build prompt
            system_prompt = """You are an expert CDM field filling assistant.
Help users fill missing required fields in their CDM data.

For each missing field:
1. Explain what the field represents
2. Ask clarifying questions if needed
3. Provide example values
4. Suggest values based on existing CDM data when possible
5. Consider deal context if provided (deal type, status, etc.)

Be helpful and guide users through the process step by step."""
            
            user_prompt = f"""Current CDM Data:
{json.dumps(cdm_data, indent=2, default=str)}

Missing Required Fields:
{json.dumps(missing_fields, indent=2)}

Conversation Context:
{conversation_context or 'No specific context provided'}
{deal_context_str}

CDM Schema Context:
{chr(10).join([doc['content'] for doc in schema_context]) if schema_context else 'No schema context available'}

Help fill the missing fields. Provide:
1. Questions to ask the user for each missing field
2. Suggested values based on existing data and deal context
3. Example values for reference"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Try to extract structured suggestions
            suggestions = self._parse_field_suggestions(response_text, missing_fields, cdm_data)
            
            return {
                "all_fields_present": False,
                "missing_fields": missing_fields,
                "suggestions": suggestions,
                "guidance": response_text,
                "questions": self._extract_questions(response_text),
            }
        except Exception as e:
            logger.error(f"Field filling failed: {e}", exc_info=True)
            return {
                "all_fields_present": False,
                "missing_fields": missing_fields if 'missing_fields' in locals() else [],
                "error": str(e),
            }
    
    def _cdm_to_text(self, cdm_data: Dict[str, Any]) -> str:
        """Convert CDM data to text representation."""
        text_parts = []
        
        if "parties" in cdm_data and isinstance(cdm_data["parties"], list):
            for party in cdm_data["parties"]:
                if isinstance(party, dict):
                    name = party.get("name", "")
                    role = party.get("role", "")
                    if name:
                        text_parts.append(f"Party: {name} ({role})")
        
        if "facilities" in cdm_data and isinstance(cdm_data["facilities"], list):
            for facility in cdm_data["facilities"]:
                if isinstance(facility, dict):
                    facility_name = facility.get("facility_name", "")
                    if facility_name:
                        text_parts.append(f"Facility: {facility_name}")
        
        if "governing_law" in cdm_data:
            text_parts.append(f"Governing Law: {cdm_data['governing_law']}")
        
        if "sustainability_linked" in cdm_data and cdm_data["sustainability_linked"]:
            text_parts.append("Sustainability-Linked Loan")
        
        return " | ".join(text_parts) if text_parts else json.dumps(cdm_data, default=str)
    
    def _identify_missing_fields(
        self,
        cdm_data: Dict[str, Any],
        required_fields: List[str],
    ) -> List[str]:
        """Identify which required fields are missing from CDM data."""
        missing = []
        
        for field_path in required_fields:
            if not self._field_exists(cdm_data, field_path):
                missing.append(field_path)
        
        return missing
    
    def _field_exists(self, data: Dict[str, Any], field_path: str) -> bool:
        """Check if a field path exists in the data structure."""
        try:
            parts = field_path.split('.')
            current = data
            
            for part in parts:
                if '[' in part:
                    # Handle array access like "facilities[0].facility_name"
                    key, index = part.split('[')
                    index = int(index.rstrip(']'))
                    if key:
                        current = current.get(key, [])
                    if not isinstance(current, list) or index >= len(current):
                        return False
                    current = current[index]
                else:
                    if not isinstance(current, dict) or part not in current:
                        return False
                    current = current[part]
            
            return current is not None
        except (KeyError, IndexError, TypeError, ValueError):
            return False
    
    def _parse_template_suggestions(
        self,
        response_text: str,
        available_templates: Optional[List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        """Parse template suggestions from LLM response."""
        suggestions = []
        
        # Try to extract template names/codes from response
        if available_templates:
            for template in available_templates:
                template_name = template.get("name", "").lower()
                template_code = template.get("template_code", "").lower()
                
                if template_name in response_text.lower() or template_code in response_text.lower():
                    suggestions.append({
                        "template_id": template.get("id"),
                        "template_code": template.get("template_code"),
                        "name": template.get("name"),
                        "category": template.get("category"),
                        "confidence": "high" if template_name in response_text.lower() else "medium",
                    })
        
        return suggestions[:3]  # Return top 3 suggestions
    
    def _parse_field_suggestions(
        self,
        response_text: str,
        missing_fields: List[str],
        cdm_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Parse field suggestions from LLM response."""
        suggestions = {}
        
        # Try to extract field suggestions from response
        for field in missing_fields:
            # Look for field mentions in response
            if field in response_text:
                suggestions[field] = {
                    "mentioned": True,
                    "guidance": response_text,
                }
        
        return suggestions
    
    def _extract_questions(self, text: str) -> List[str]:
        """Extract questions from response text."""
        questions = []
        lines = text.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.endswith('?') and ('?' in line):
                questions.append(line)
        
        return questions
    
    def add_to_knowledge_base(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        doc_id: Optional[str] = None,
    ) -> None:
        """Add content to the knowledge base.
        
        Args:
            content: Text content to add
            metadata: Optional metadata (source, type, etc.)
            doc_id: Optional document ID (auto-generated if not provided)
        """
        try:
            if doc_id is None:
                import uuid
                doc_id = str(uuid.uuid4())
            
            # Generate embedding
            embedding = self.embeddings_model.embed_query(content)
            
            # Prepare metadata
            doc_metadata = metadata or {}
            doc_metadata["content_type"] = doc_metadata.get("content_type", "general")
            
            # Add to collection
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[doc_metadata],
            )
            
            logger.info(f"Added document to knowledge base: {doc_id}")
        except Exception as e:
            logger.error(f"Failed to add to knowledge base: {e}")
            raise
    
    def get_kb_stats(self) -> Dict[str, Any]:
        """Get knowledge base statistics."""
        try:
            count = self.collection.count()
            return {
                "document_count": count,
                "collection_name": self.kb_collection_name,
            }
        except Exception as e:
            logger.error(f"Failed to get KB stats: {e}")
            return {"error": str(e)}















