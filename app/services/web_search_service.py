"""Web search service vendored from dev/app.py, adapted to repository patterns.

Follows existing service layer patterns:
- Service class with dependency injection
- Rate limiting using limits library
- Analytics integration
- CDM event generation for search operations
"""

import logging
import asyncio
import time
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from functools import lru_cache
import httpx
import trafilatura
from dateutil import parser as dateparser
from limits import parse
from limits.aio.storage import MemoryStorage
from limits.aio.strategies import MovingWindowRateLimiter

from app.core.config import settings
from app.core import data_cache as dc
from app.services.web_search_analytics import (
    record_request,
    last_n_days_df,
    last_n_days_avg_time_df
)

logger = logging.getLogger(__name__)

# Rate limiting (from dev/app.py)
storage = MemoryStorage()
limiter = MovingWindowRateLimiter(storage)
rate_limit = parse("360/hour")  # Configurable via settings


class WebSearchService:
    """
    Web search service following repository patterns.
    
    Adapted from dev/app.py with:
    - Service layer pattern
    - Configuration via settings
    - CDM event generation
    - Local/remote reranking support
    """
    
    def __init__(
        self,
        serper_api_key: Optional[str] = None,
        use_local_reranking: bool = None,
        reranking_model: Optional[str] = None
    ):
        """
        Initialize web search service.
        
        Args:
            serper_api_key: Serper API key (default: settings.SERPER_API_KEY)
            use_local_reranking: Use local reranking model (default: settings.RERANKING_USE_LOCAL)
            reranking_model: Reranking model identifier (default: settings.RERANKING_MODEL)
        """
        # Get API key from settings (SecretStr) or parameter
        if serper_api_key:
            self.serper_api_key = serper_api_key
        elif hasattr(settings, "SERPER_API_KEY") and settings.SERPER_API_KEY:
            self.serper_api_key = settings.SERPER_API_KEY.get_secret_value()
        else:
            self.serper_api_key = None
        self.serper_search_endpoint = "https://google.serper.dev/search"
        self.serper_news_endpoint = "https://google.serper.dev/news"
        
        # Reranking configuration
        self.use_local_reranking = (
            use_local_reranking 
            if use_local_reranking is not None 
            else getattr(settings, "RERANKING_USE_LOCAL", False)
        )
        self.reranking_model = (
            reranking_model or 
            getattr(settings, "RERANKING_MODEL", "BAAI/bge-reranker-base")
        )
        self.reranking_device = getattr(settings, "RERANKING_DEVICE", "cpu")
        
        # Initialize reranking model if using local
        self._reranker = None
        if self.use_local_reranking:
            self._init_local_reranker()
    
    def _init_local_reranker(self):
        """Initialize local reranking model following embeddings pattern."""
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info(
                f"Initializing local reranking model: {self.reranking_model} "
                f"on device: {self.reranking_device}"
            )
            
            self._reranker = CrossEncoder(
                self.reranking_model,
                device=self.reranking_device
            )
        except ImportError:
            logger.warning(
                "sentence-transformers not available for local reranking. "
                "Falling back to remote reranking."
            )
            self.use_local_reranking = False
        except Exception as e:
            logger.error(f"Failed to initialize local reranker: {e}")
            self.use_local_reranking = False
    
    async def search_web(
        self,
        query: str,
        search_type: str = "search",
        num_results: Optional[int] = 4,
        rerank: bool = True,
        top_k_after_rerank: Optional[int] = None,
        db: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Search the web and optionally rerank results.
        
        Follows pattern from dev/app.py with enhancements:
        - Reranking support (local or remote)
        - CDM event generation
        - Analytics integration
        - Optional caching via data_cache when db is provided (else in-memory)
        
        Args:
            query: Search query
            search_type: "search" or "news"
            num_results: Number of results to fetch (1-20)
            rerank: Whether to rerank results (default: True)
            top_k_after_rerank: Number of results after reranking (default: num_results)
            db: Optional DB session for DataCache; None for in-memory only.
            
        Returns:
            Dict with search results, metadata, and CDM event
        """
        start_time = time.time()
        
        # Validate inputs
        if num_results is None:
            num_results = 4
        num_results = max(1, min(20, num_results))
        
        if search_type not in ["search", "news"]:
            search_type = "search"
        
        tk = top_k_after_rerank if top_k_after_rerank is not None else num_results
        cache_key = dc.make_key("web_search", query, search_type, num_results, rerank, tk)
        cached = dc.get(cache_key, db)
        if cached is not None:
            return cached
        
        # Serper is the default and required web search backend
        if not self.serper_api_key:
            duration = time.time() - start_time
            await record_request(duration, num_results or 4)
            raise ValueError(
                "SERPER_API_KEY not configured. "
                "Set SERPER_API_KEY (get from https://serper.dev) to use web search."
            )
        
        try:
            # Check rate limit
            if not await limiter.hit(rate_limit, "global"):
                logger.warning("Rate limit exceeded")
                duration = time.time() - start_time
                await record_request(duration, num_results)
                raise ValueError(
                    "Rate limit exceeded. Please try again later "
                    "(limit: 360 requests per hour)."
                )
            
            # Select endpoint
            endpoint = (
                self.serper_news_endpoint 
                if search_type == "news" 
                else self.serper_search_endpoint
            )
            
            # Prepare payload
            payload = {"q": query, "num": num_results}
            if search_type == "news":
                payload["type"] = "news"
                payload["page"] = 1
            
            # Execute search
            async with httpx.AsyncClient(timeout=15) as client:
                headers = {
                    "X-API-KEY": self.serper_api_key,
                    "Content-Type": "application/json"
                }
                resp = await client.post(endpoint, headers=headers, json=payload)
            
            if resp.status_code != 200:
                duration = time.time() - start_time
                await record_request(duration, num_results)
                raise ValueError(
                    f"Search API returned status {resp.status_code}. "
                    "Please check your API key and try again."
                )
            
            # Extract results
            if search_type == "news":
                results = resp.json().get("news", [])
            else:
                results = resp.json().get("organic", [])
            
            if not results:
                duration = time.time() - start_time
                await record_request(duration, num_results)
                out = {
                    "query": query,
                    "search_type": search_type,
                    "results": [],
                    "extracted_content": [],
                    "cdm_event": None,
                    "duration": duration,
                }
                dc.set(cache_key, out, dc.TTL_WEB_SEARCH, dc.SOURCE_WEB_SEARCH, dc.KIND_PUNCTUAL, db)
                return out
            
            # Fetch and extract content
            urls = [r["link"] for r in results]
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                tasks = [client.get(u) for u in urls]
                responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Extract content with trafilatura
            chunks = []
            for meta, response in zip(results, responses):
                if isinstance(response, Exception):
                    continue
                
                body = trafilatura.extract(
                    response.text,
                    include_formatting=True,
                    include_comments=False
                )
                
                if not body:
                    continue
                
                # Format chunk
                if search_type == "news":
                    try:
                        date_str = meta.get("date", "")
                        date_iso = (
                            dateparser.parse(date_str, fuzzy=True).strftime("%Y-%m-%d")
                            if date_str else "Unknown"
                        )
                    except Exception:
                        date_iso = "Unknown"
                    
                    chunk = {
                        "title": meta.get("title", ""),
                        "source": meta.get("source", "Unknown"),
                        "date": date_iso,
                        "url": meta.get("link", ""),
                        "content": body.strip()
                    }
                else:
                    domain = meta["link"].split("/")[2].replace("www.", "")
                    chunk = {
                        "title": meta.get("title", ""),
                        "domain": domain,
                        "url": meta.get("link", ""),
                        "content": body.strip()
                    }
                
                chunks.append(chunk)
            
            # Fallback: when trafilatura extracts nothing, use snippet so agents get usable content
            if not chunks and results:
                for meta in results:
                    link = meta.get("link", "")
                    snippet = meta.get("snippet", "")
                    domain = (link.split("/")[2].replace("www.", "") if len(link.split("/")) > 2 else "") if link else ""
                    if search_type == "news":
                        try:
                            date_str = meta.get("date", "")
                            date_iso = dateparser.parse(date_str, fuzzy=True).strftime("%Y-%m-%d") if date_str else ""
                        except Exception:
                            date_iso = ""
                        chunks.append({
                            "title": meta.get("title", ""),
                            "source": meta.get("source", domain),
                            "domain": domain,
                            "date": date_iso,
                            "url": link,
                            "content": snippet or "(No content extracted)"
                        })
                    else:
                        chunks.append({
                            "title": meta.get("title", ""),
                            "domain": domain,
                            "source": domain,
                            "url": link,
                            "content": snippet or "(No content extracted)"
                        })
                chunks = chunks[: num_results]
            
            # Rerank results if enabled
            if rerank and chunks:
                chunks = await self._rerank_results(query, chunks, top_k_after_rerank or num_results)
            
            # Generate CDM event (TODO: Add generate_cdm_research_query to app/models/cdm_events.py)
            # For now, create a simple research query event structure
            cdm_event = {
                "eventType": "ResearchQuery",
                "eventDate": datetime.now(timezone.utc).isoformat(),
                "query": {
                    "queryText": query,
                    "searchType": search_type,
                    "numResults": len(chunks),
                    "sources": [chunk["url"] for chunk in chunks]
                },
                "meta": {
                    "globalKey": str(uuid.uuid4()),
                    "sourceSystem": "CreditNexus_WebSearch",
                    "version": 1
                }
            }
            
            # Record analytics
            duration = time.time() - start_time
            await record_request(duration, num_results)
            
            out = {
                "query": query,
                "search_type": search_type,
                "results": results,
                "extracted_content": chunks,
                "cdm_event": cdm_event,
                "duration": duration,
            }
            dc.set(cache_key, out, dc.TTL_WEB_SEARCH, dc.SOURCE_WEB_SEARCH, dc.KIND_PUNCTUAL, db)
            return out
            
        except Exception as e:
            duration = time.time() - start_time
            await record_request(duration, num_results)
            logger.error(f"Web search failed: {e}")
            raise
    
    async def _rerank_results(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int
    ) -> List[Dict[str, Any]]:
        """
        Rerank search results using local or remote reranking.
        
        Args:
            query: Original search query
            chunks: List of content chunks to rerank
            top_k: Number of top results to return
            
        Returns:
            Reranked list of chunks
        """
        if not chunks:
            return []
        
        if self.use_local_reranking and self._reranker:
            # Local reranking using CrossEncoder
            try:
                # Prepare pairs: (query, content) for each chunk
                pairs = [
                    (query, chunk.get("content", chunk.get("title", "")))
                    for chunk in chunks
                ]
                
                # Get reranking scores
                scores = self._reranker.predict(pairs)
                
                # Sort by score (descending)
                scored_chunks = list(zip(chunks, scores))
                scored_chunks.sort(key=lambda x: x[1], reverse=True)
                
                # Return top_k
                reranked = [chunk for chunk, score in scored_chunks[:top_k]]
                
                logger.info(
                    f"Reranked {len(chunks)} results to top {len(reranked)} "
                    f"using local model"
                )
                
                return reranked
                
            except Exception as e:
                logger.warning(f"Local reranking failed: {e}. Using original order.")
                return chunks[:top_k]
        else:
            # Remote reranking using API (e.g., Cohere, Jina)
            # For now, return top_k without reranking
            # TODO: Implement remote reranking API integration
            logger.info("Remote reranking not yet implemented. Using original order.")
            return chunks[:top_k]


@lru_cache(maxsize=1)
def get_web_search_service() -> WebSearchService:
    """Get or create singleton web search service instance."""
    return WebSearchService()
