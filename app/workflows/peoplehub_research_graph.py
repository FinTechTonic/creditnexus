"""PeopleHub research workflow using LangGraph.

Ports TypeScript LangGraph workflow to Python following existing patterns.
"""

import logging
from typing import Optional, Dict, Any, List, TypedDict
from datetime import datetime

try:
    from langgraph.graph import StateGraph, END
    from langgraph.graph.message import add_messages
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    logger.warning("LangGraph not available. PeopleHub workflow will use simplified implementation.")

from langchain_core.messages import HumanMessage, AIMessage

from app.core.llm_client import get_chat_model
from app.services.web_search_service import get_web_search_service

logger = logging.getLogger(__name__)


class ResearchState(TypedDict):
    """Research state following PeopleHub pattern."""
    person_name: str
    linkedin_url: Optional[str]
    linkedin_data: Optional[Dict[str, Any]]
    search_query: Optional[str]
    search_results: List[Dict[str, Any]]
    scraped_contents: List[Dict[str, Any]]
    web_summaries: List[Dict[str, Any]]
    final_report: Optional[str]
    errors: List[str]
    status: str


def create_peoplehub_research_graph():
    """
    Create PeopleHub research graph using LangGraph.
    
    Follows PeopleHub workflow:
    1. Fetch LinkedIn profile
    2. Generate search query
    3. Execute search
    4. Scrape web pages (parallel)
    5. Summarize content (parallel)
    6. Aggregate data
    7. Write report
    """
    if not LANGGRAPH_AVAILABLE:
        # Fallback to simple sequential execution
        logger.warning("LangGraph not available, using simplified workflow")
        return None
    
    from langgraph.graph import StateGraph, END
    
    workflow = StateGraph(ResearchState)
    
    # Add nodes
    workflow.add_node("start", start_node)
    workflow.add_node("fetch_linkedin", fetch_linkedin_node)
    workflow.add_node("generate_search_query", generate_search_query_node)
    workflow.add_node("execute_search", execute_search_node)
    workflow.add_node("scrape_web_page", scrape_web_page_node)
    workflow.add_node("summarize_content", summarize_content_node)
    workflow.add_node("aggregate_data", aggregate_data_node)
    workflow.add_node("write_report", write_report_node)
    
    # Define edges
    workflow.set_entry_point("start")
    # NOTE: Avoid parallel fan-out from "start" because LangGraph LastValue channels
    # cannot accept multiple writes to the same key in a single step (e.g., "status").
    # Keep this workflow sequential to prevent INVALID_CONCURRENT_GRAPH_UPDATE.
    workflow.add_edge("start", "fetch_linkedin")
    workflow.add_edge("fetch_linkedin", "generate_search_query")
    workflow.add_conditional_edges(
        "generate_search_query",
        lambda state: "execute_search" if state.get("search_query") else "aggregate_data"
    )
    workflow.add_conditional_edges(
        "execute_search",
        route_to_scraping,
        {
            "scrape": "scrape_web_page",
            "skip": "aggregate_data"
        }
    )
    workflow.add_conditional_edges(
        "scrape_web_page",
        route_to_summarization,
        {
            "summarize": "summarize_content",
            "skip": "aggregate_data"
        }
    )
    workflow.add_edge("summarize_content", "aggregate_data")
    workflow.add_edge("aggregate_data", "write_report")
    workflow.add_edge("write_report", END)
    
    return workflow.compile()


def start_node(state: ResearchState) -> Dict[str, Any]:
    """Initialize research state."""
    return {
        "status": "Initializing research...",
        "errors": [],
        "search_results": [],
        "scraped_contents": [],
        "web_summaries": []
    }


def fetch_linkedin_node(state: ResearchState) -> Dict[str, Any]:
    """Fetch LinkedIn profile data."""
    # Implementation: Use Bright Data LinkedIn API or similar
    # This would integrate with existing LinkedIn scraping infrastructure
    logger.info(f"Fetching LinkedIn profile: {state.get('linkedin_url', 'N/A')}")
    # Placeholder - implement actual LinkedIn fetching
    # For now, return empty data
    # Only return fields that are being updated to avoid concurrent update errors
    return {
        "linkedin_data": {},
        "status": "Fetched LinkedIn profile"
    }


def generate_search_query_node(state: ResearchState) -> Dict[str, Any]:
    """Generate search query from person name and LinkedIn data."""
    llm = get_chat_model(temperature=0.7)
    
    prompt = f"""Generate a Google search query to find information about {state['person_name']}.
    
LinkedIn Data:
{state.get('linkedin_data', {})}

Generate a search query that will find:
- Recent projects and achievements
- News articles and press releases
- Professional publications
- Industry recognition

Return only the search query, nothing else.
"""
    
    try:
        response = llm.invoke(prompt)
        search_query = response.content.strip()
        
        # Only return fields that are being updated to avoid concurrent update errors
        return {
            "search_query": search_query,
            "status": "Generated search query"
        }
    except Exception as e:
        logger.error(f"Error generating search query: {e}")
        # Only return fields that are being updated
        return {
            "errors": state.get("errors", []) + [f"Search query generation failed: {str(e)}"],
            "status": "Error generating search query"
        }


async def execute_search_node(state: ResearchState) -> Dict[str, Any]:
    """Execute web search using WebSearchService (LangChain-compatible return shape)."""
    search_query = state.get("search_query")
    if not search_query:
        return {"status": "No search query to execute"}

    try:
        service = get_web_search_service()
        logger.info(f"Executing search: {search_query}")
        result = await service.search_web(
            query=search_query,
            search_type="search",
            num_results=8,
            rerank=True,
            top_k_after_rerank=6,
        )
        # Map extracted_content to search_results: [{url, title, content}] for scrape_web_page
        extracted = result.get("extracted_content", [])
        search_results = [
            {"url": c.get("url", ""), "title": c.get("title", ""), "content": c.get("content", "")}
            for c in extracted
        ]
        return {"search_results": search_results, "status": "Executed search"}
    except Exception as e:
        logger.error(f"Error executing search: {e}")
        return {
            "errors": state.get("errors", []) + [f"Search execution failed: {str(e)}"],
            "status": "Error executing search",
        }


def scrape_web_page_node(state: ResearchState) -> Dict[str, Any]:
    """Use search result content; WebSearchService already extracted content in execute_search."""
    search_results = state.get("search_results", [])
    if not search_results:
        return {"status": "No search results to scrape"}

    logger.info("Using web search content for summarization")
    scraped_contents = []
    for result in search_results[:5]:
        url = result.get("url", "")
        if url:
            # Content already from WebSearchService.extracted_content when available
            scraped_contents.append({
                "url": url,
                "content": result.get("content", ""),
                "title": result.get("title", ""),
            })
    return {"scraped_contents": scraped_contents, "status": "Scraped web pages"}


def summarize_content_node(state: ResearchState) -> Dict[str, Any]:
    """Summarize scraped content."""
    llm = get_chat_model(temperature=0)
    
    summaries = []
    for content in state.get("scraped_contents", []):
        prompt = f"""Summarize the following content about {state['person_name']}:

Content:
{content.get('content', '')}

Focus on:
- Professional achievements
- Recent projects
- Industry recognition
- Key skills and expertise

Return a concise summary.
"""
        try:
            response = llm.invoke(prompt)
            summaries.append({
                "url": content.get("url", ""),
                "summary": response.content,
                "key_points": [],
                "mentions_person": True,
                "confidence": 0.8
            })
        except Exception as e:
            logger.warning(f"Error summarizing content from {content.get('url', '')}: {e}")
            continue
    
    return {
        "web_summaries": summaries,
        "status": "Summarized content"
    }


def aggregate_data_node(state: ResearchState) -> Dict[str, Any]:
    """Aggregate all research data."""
    # Deduplicate and merge data
    web_summaries = state.get("web_summaries", [])
    linkedin_data = state.get("linkedin_data", {})
    
    return {
        "status": "Aggregated data"
    }


def write_report_node(state: ResearchState) -> Dict[str, Any]:
    """Generate final research report."""
    llm = get_chat_model(temperature=0.7)
    
    prompt = f"""Generate a comprehensive research report about {state['person_name']}.

LinkedIn Data:
{state.get('linkedin_data', {})}

Web Summaries:
{state.get('web_summaries', [])}

Generate a report covering:
1. Professional Background
2. Recent Projects and Achievements
3. Technical Expertise
4. Industry Reputation
5. Sources

Format as Markdown.
"""
    
    try:
        response = llm.invoke(prompt)
        report = response.content
        
        return {
            "final_report": report,
            "status": "Report ready"
        }
    except Exception as e:
        logger.error(f"Error writing report: {e}")
        return {
            "errors": state.get("errors", []) + [f"Report generation failed: {str(e)}"],
            "status": "Error generating report"
        }


def route_to_scraping(state: ResearchState) -> str:
    """Route to scraping if search results available."""
    if state.get("search_results"):
        return "scrape"
    return "skip"


def route_to_summarization(state: ResearchState) -> str:
    """Route to summarization if scraped content available."""
    if state.get("scraped_contents"):
        return "summarize"
    return "skip"


async def execute_peoplehub_research(
    person_name: str,
    linkedin_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Execute PeopleHub research workflow.
    
    Args:
        person_name: Name of the person to research
        linkedin_url: Optional LinkedIn profile URL
        
    Returns:
        Research result with final report and data
    """
    graph = create_peoplehub_research_graph()
    
    if graph is None:
        # Fallback: Execute nodes sequentially without LangGraph
        logger.info("Using simplified sequential workflow")
        state: ResearchState = {
            "person_name": person_name,
            "linkedin_url": linkedin_url,
            "linkedin_data": None,
            "search_query": None,
            "search_results": [],
            "scraped_contents": [],
            "web_summaries": [],
            "final_report": None,
            "errors": [],
            "status": "initializing"
        }
        
        # Execute nodes sequentially
        state = start_node(state)
        state = fetch_linkedin_node(state)
        state = generate_search_query_node(state)
        if state.get("search_query"):
            state = await execute_search_node(state)
            if state.get("search_results"):
                state = scrape_web_page_node(state)
                if state.get("scraped_contents"):
                    state = summarize_content_node(state)
        state = aggregate_data_node(state)
        state = write_report_node(state)
        
        return state
    else:
        # Use LangGraph workflow
        initial_state: ResearchState = {
            "person_name": person_name,
            "linkedin_url": linkedin_url,
            "linkedin_data": None,
            "search_query": None,
            "search_results": [],
            "scraped_contents": [],
            "web_summaries": [],
            "final_report": None,
            "errors": [],
            "status": "initializing"
        }
        
        result = await graph.ainvoke(initial_state)
        return result
