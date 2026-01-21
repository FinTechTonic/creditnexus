"""DeepResearch orchestrator agent using LangChain.

Ports node-DeepResearch iterative research pattern to Python using LangChain.
Follows existing agent patterns from app/agents/analyzer.py
"""

import logging
import uuid
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from langchain_core.language_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage
from langgraph.prebuilt import create_react_agent
from langchain_core.prompts import MessagesPlaceholder

from app.core.llm_client import get_chat_model
from app.agents.deep_research_tools import get_all_research_tools, research_context_var

logger = logging.getLogger(__name__)


class ResearchAction(str, Enum):
    """Research actions following DeepResearch pattern."""
    SEARCH = "search"
    READ = "read"
    ANSWER = "answer"
    REFLECT = "reflect"
    CODING = "coding"


@dataclass
class KnowledgeItem:
    """Knowledge item accumulated during research."""
    question: str
    answer: str
    references: List[str]
    type: str  # 'url', 'qa', 'side-info', 'coding'
    updated: Optional[str] = None


@dataclass
class ResearchContext:
    """Research context tracking."""
    token_budget: int = 1000000
    visited_urls: List[str] = field(default_factory=list)
    knowledge_items: List[KnowledgeItem] = field(default_factory=list)
    searched_queries: List[str] = field(default_factory=list)
    all_urls: Dict[str, Any] = field(default_factory=dict)


def create_deep_research_agent():
    """
    Create DeepResearch agent using LangGraph ReAct pattern.
    
    Follows existing agent patterns:
    - Uses get_chat_model() for LLM
    - Creates ReAct agent with tools using langgraph.prebuilt
    - Returns LangGraph graph for execution (supports ainvoke)
    """
    llm = get_chat_model(temperature=0.7)  # Slightly higher for reasoning
    
    # Create tools for research actions
    tools = get_all_research_tools()
    
    # Create ReAct agent using langgraph.prebuilt (returns a graph)
    # This graph can be invoked directly with ainvoke()
    agent = create_react_agent(llm, tools)
    
    return agent


async def research_query(
    question: str,
    context: Optional[ResearchContext] = None,
    deal_id: Optional[int] = None,
    workflow_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Execute DeepResearch query with CDM event integration.
    
    Args:
        question: Research question
        context: Optional research context
        deal_id: Optional deal ID for CDM event linking
        workflow_id: Optional workflow ID for CDM event linking
        
    Returns:
        Research result with answer, knowledge items, and CDM events
    """
    if context is None:
        context = ResearchContext()
    
    # Create agent
    agent = create_deep_research_agent()
    
    # Collector for visited_urls and searched_queries (tools append via research_context_var)
    collector: dict = {"visited_urls": [], "searched_queries": []}
    tok = research_context_var.set(collector)
    try:
        # Execute research - langgraph.prebuilt.create_react_agent expects {"messages": [message]}
        question_with_context = f"{question}\n\nContext: {str(context)}" if context else question
        message = HumanMessage(content=question_with_context)
        result = await agent.ainvoke({"messages": [message]})
    finally:
        research_context_var.reset(tok)
    
    visited_urls = collector.get("visited_urls") or []
    searched_queries = collector.get("searched_queries") or []
    
    # Extract answer from result - langgraph returns {"messages": [...]}
    response_messages = result.get("messages", [])
    answer = response_messages[-1].content if response_messages and isinstance(response_messages[-1], AIMessage) else ""
    
    # Generate CDM event for research completion
    research_event = {
        "eventType": "ResearchQuery",
        "eventDate": datetime.now().isoformat(),
        "researchQuery": {
            "query": question,
            "answer": answer,
            "knowledgeItems": [item.__dict__ for item in context.knowledge_items],
            "visitedUrls": visited_urls,
            "searchedQueries": searched_queries
        },
        "meta": {
            "globalKey": str(uuid.uuid4()),
            "sourceSystem": "CreditNexus_DeepResearch_v1",
            "version": 1
        }
    }
    
    # Link to deal/workflow if provided
    if deal_id:
        research_event["relatedEventIdentifier"] = [{
            "eventIdentifier": {
                "issuer": "CreditNexus",
                "assignedIdentifier": [{"identifier": {"value": f"DEAL_{deal_id}"}}]
            }
        }]
    
    return {
        "answer": answer,
        "knowledge_items": [item.__dict__ for item in context.knowledge_items],
        "visited_urls": visited_urls,
        "searched_queries": searched_queries,
        "cdm_event": research_event
    }
