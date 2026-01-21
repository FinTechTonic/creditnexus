"""DeepResearch tools for web search, URL reading, and query processing.

Tools are separated from the main agent for better organization and reusability.
When the ReAct agent calls tool.run() (sync), func must be sync; we use _run_async_sync
to run the async implementation. coroutine= is used when the framework calls ainvoke.

research_context_var: optional per-request collector for visited_urls and searched_queries.
Set by research_query() before ainvoke; tools append to it so the detail view can show sources.
"""

import asyncio
import contextvars
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List, Any
import httpx
import trafilatura

from langchain_core.tools import StructuredTool

from app.core.llm_client import get_chat_model
from app.services.web_search_service import get_web_search_service

logger = logging.getLogger(__name__)

# Set by research_query() before ainvoke; search_web/read_url append visited_urls and searched_queries
research_context_var: contextvars.ContextVar[dict] = contextvars.ContextVar("research_context", default={})


def _run_async_sync(coro):
    """Run an async coroutine from a sync context. Safe when an event loop is already running."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with ThreadPoolExecutor(max_workers=1) as ex:
        return ex.submit(asyncio.run, coro).result()


def create_search_tool() -> StructuredTool:
    """Create web search tool using WebSearchService."""
    service = get_web_search_service()

    async def search_web(query: str) -> str:
        """Search the web for information."""
        try:
            result = await service.search_web(
                query=query,
                search_type="search",
                num_results=4,
                rerank=True
            )
            try:
                ctx = research_context_var.get()
                if isinstance(ctx, dict):
                    ctx.setdefault("searched_queries", []).append(query)
                    seen = set(ctx.setdefault("_urls_seen", set()))
                    for c in result.get("extracted_content") or []:
                        u = c.get("url") if isinstance(c, dict) else None
                        if u and u not in seen:
                            seen.add(u)
                            ctx.setdefault("visited_urls", []).append(u)
            except LookupError:
                pass
            formatted = []
            for chunk in result.get("extracted_content", []):
                formatted.append(
                    f"## {chunk.get('title', 'Untitled')}\n"
                    f"**URL:** {chunk.get('url', '')}\n\n"
                    f"{chunk.get('content', '')}\n"
                )
            return "\n---\n".join(formatted) if formatted else "No results found."
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return f"Search error: {str(e)}"

    return StructuredTool.from_function(
        func=lambda query: _run_async_sync(search_web(query)),
        coroutine=search_web,
        name="web_search",
        description="Search the web for information. Use this when you need to find information about a topic.",
    )


def create_read_url_tool() -> StructuredTool:
    """Create URL reading tool: fetches the page and extracts main content."""
    async def read_url(url: str) -> str:
        """Read content from a URL."""
        try:
            try:
                ctx = research_context_var.get()
                if isinstance(ctx, dict) and url:
                    seen = ctx.setdefault("_urls_seen", set())
                    if url not in seen:
                        seen.add(url)
                        ctx.setdefault("visited_urls", []).append(url)
            except LookupError:
                pass
            async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                text = resp.text
            body = trafilatura.extract(text, include_formatting=True, include_comments=False)
            return (body or text[:8000] or f"Could not extract content from: {url}").strip()
        except Exception as e:
            logger.warning(f"URL reading failed: {e}")
            return f"Error reading URL: {str(e)}"

    return StructuredTool.from_function(
        func=lambda url: _run_async_sync(read_url(url)),
        coroutine=read_url,
        name="read_url",
        description="Read content from a URL. Use this to get detailed information from a webpage.",
    )


def create_answer_evaluator_tool() -> StructuredTool:
    """Create answer evaluation tool."""
    async def evaluate_answer(question: str, answer: str) -> str:
        """Evaluate if an answer is complete and accurate."""
        llm = get_chat_model(temperature=0.3)
        prompt = f"""Evaluate if the following answer is complete and accurate for the question:

Question: {question}

Answer: {answer}

Respond with: "COMPLETE" if the answer fully addresses the question, or "INCOMPLETE" with specific missing information.
"""
        response = await llm.ainvoke(prompt)
        return response.content

    return StructuredTool.from_function(
        func=lambda question, answer: _run_async_sync(evaluate_answer(question, answer)),
        coroutine=evaluate_answer,
        name="evaluate_answer",
        description="Evaluate if an answer is complete and accurate. Use this to check answer quality.",
    )


def create_query_rewriter_tool() -> StructuredTool:
    """Create query rewriter tool."""
    async def rewrite_query(original_query: str, context: str = "") -> str:
        """Rewrite a search query based on context."""
        llm = get_chat_model(temperature=0.7)
        prompt = f"""Rewrite the following search query to improve search results based on the context:

Original Query: {original_query}

Context: {context if context else 'No additional context'}

Return only the improved search query, nothing else.
"""
        response = await llm.ainvoke(prompt)
        return response.content.strip()

    def _rewrite_sync(original_query: str, context: str = "") -> str:
        return _run_async_sync(rewrite_query(original_query, context))

    return StructuredTool.from_function(
        func=_rewrite_sync,
        coroutine=rewrite_query,
        name="rewrite_query",
        description="Rewrite a search query to improve search results. Use this to refine queries.",
    )


def get_all_research_tools() -> List[Any]:
    """Get all research tools for DeepResearch agent."""
    return [
        create_search_tool(),
        create_read_url_tool(),
        create_answer_evaluator_tool(),
        create_query_rewriter_tool()
    ]
