"""
Vector Store for 'Deep Tech' Semantic Search.
Implements a hybrid vector store that acts as a bridge between Financial States and Semantic Queries.
"""

import logging
import json
import numpy as np
import uuid
from typing import List, Dict, Any, Optional

# Constants
EMBEDDING_DIM = 1536  # OpenAI text-embedding-ada-002
MOCK_EMBEDDINGS = False

logger = logging.getLogger(__name__)

class TradeVectorStore:
    """
    Manages embedding and retrieval of Trade State definitions.
    Uses numpy for in-memory cosine similarity (Lite Implementation).
    """

    def __init__(self):
        self.vectors = []
        self.metadata = []
        self.ids = []
        logger.info("Initialized In-Memory Vector Store.")

    def _get_embedding(self, text: str) -> List[float]:
        """
        Generates an embedding for the text.
        In a real deployment, calls OpenAI API.
        For Kill Shot Demo, we can use a mock or try real if api key present.
        """
        try:
            # Check for langchain_openai
            from langchain_openai import OpenAIEmbeddings
            import os
            
            if os.getenv("OPENAI_API_KEY"):
               embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
               return embeddings.embed_query(text)
            
        except Exception as e:
            logger.warning(f"Embedding Model skipped: {e}")
        
        # Fallback: Deterministic 'Mock' Embedding seeded by text definition
        # This keeps the demo running even offline
        seed = len(text)
        np.random.seed(seed)
        return np.random.rand(EMBEDDING_DIM).tolist()

    def add_trade_event(self, event: Dict[str, Any]):
        """
        Ingests a CDM Event JSON, vectorizes its semantic content, and indexes it.
        """
        try:
            event_id = event.get("meta", {}).get("globalKey", str(uuid.uuid4()))
            event_type = event.get("eventType", "Unknown")
            
            # Create Semantic Representation
            # We squash the structured JSON into a narrative string for the LLM/Embedder
            semantic_text = self._jsonify_to_narrative(event)
            
            # Embed
            vector = self._get_embedding(semantic_text)
            
            # Store
            self.vectors.append(vector)
            self.metadata.append({
                "id": event_id,
                "type": event_type,
                "json": event,
                "narrative": semantic_text
            })
            self.ids.append(event_id)
            
            logger.info(f"Indexed Event: {event_type} (ID: {event_id[:8]}...)")
            
        except Exception as e:
            logger.error(f"Failed to index trade event: {e}")

    def semantic_search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Performs Cosine Similarity search over the trade history.
        """
        if not self.vectors:
            return []

        # Embed Query
        query_vector = np.array(self._get_embedding(query))
        
        # Compute Cosine Similarity
        # Sim(A, B) = dot(A, B) / (norm(A) * norm(B))
        scores = []
        for idx, doc_vector in enumerate(self.vectors):
            vec = np.array(doc_vector)
            score = np.dot(query_vector, vec) / (np.linalg.norm(query_vector) * np.linalg.norm(vec))
            scores.append((score, idx))
        
        # Sort desc
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Return Top K
        results = []
        for score, idx in scores[:top_k]:
            results.append({
                "score": float(score),
                "event": self.metadata[idx]["json"],
                "narrative": self.metadata[idx]["narrative"]
            })
            
        logger.info(f"Semantic Search '{query}' returned {len(results)} results.")
        return results

    def _jsonify_to_narrative(self, event: Dict[str, Any]) -> str:
        """Converts complex CDM JSON to a readable string for embedding."""
        event_type = event.get("eventType")
        
        if event_type == "TradeExecution":
            # Extract key economics
            try:
                economics = event["trade"]["tradableProduct"]["economicTerms"]
                notional = economics["notional"]["amount"]["value"]
                currency = economics["notional"]["currency"]["value"]
                borrower = event["trade"]["tradableProduct"]["counterparty"][1]["partyReference"]["globalReference"]
                return f"New Sustainability Linked Loan for {borrower}. Notional: {notional} {currency}. Type: TradeExecution."
            except:
                return f"Trade Execution Event for {event.get('meta', {}).get('globalKey')}"

        elif event_type == "Observation":
             try:
                 obs = event["observation"]["observedValue"]
                 status = obs["value"]
                 score = obs.get("numericValue", "N/A")
                 return f"Satellite Observation Result. Status: {status}. NDVI Score: {score}. Generated by TorchGeo."
             except:
                 return "Satellite Observation Event"

        elif event_type == "TermsChange":
             try:
                 change = event["tradeState"]["updatedEconomicTerms"]["payout"]["interestRatePayout"]["rateSpecification"]["floatingRate"]["spreadSchedule"]
                 new_val = change["initialValue"]["value"]
                 reason = event["tradeState"]["change"]["reason"]
                 return f"Interest Rate Adjustment. New Spread: {new_val}%. Reason: {reason}. Penalty Applied."
             except:
                 return "Terms Change Event (Rate Reset)"
            
        return json.dumps(event)

# Global Instance
GLOBAL_VECTOR_STORE = TradeVectorStore()
