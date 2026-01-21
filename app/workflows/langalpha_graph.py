"""LangAlpha quantitative analysis workflow using LangGraph.

Ported from dev/LangAlpha-master/src/agent/market_intelligence_agent.

Follows repository patterns:
- Uses LLM client abstraction
- Integrates with vendored tools
- CDM event generation
- Deal timeline integration
"""

import logging
import json
import os
from typing import Literal, Optional, List, Dict, Any, TypedDict
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.language_models import BaseChatModel
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langgraph.prebuilt import create_react_agent

from app.core.llm_client import get_chat_model
from app.core.config import settings
from app.utils.audit import log_audit_action
from app.db.models import AuditAction
from app.agents.langalpha_tools import (
    get_market_data,
    get_ticker_snapshot,
    get_fundamental_data,
    web_search,
    get_tickertick_news,
    browser_tool,
    python_repl_tool,
    get_trading_signals,
    LANGALPHA_TOOLS,
    set_audit_context
)

logger = logging.getLogger(__name__)

# Team members (agents)
TEAM_MEMBERS = ["researcher", "coder", "reporter", "market", "browser", "analyst"]

# Load prompts from files (will be loaded dynamically)
PROMPTS_DIR = Path(__file__).parent.parent.parent / "dev" / "LangAlpha-master" / "src" / "agent" / "market_intelligence_agent" / "prompts"


# ============================================================================
# State Definition
# ============================================================================

class TickerInfo(TypedDict, total=False):
    """Ticker information."""
    company: Optional[str]
    ticker: Optional[str]
    tradingview_symbol: Optional[str]


class State(TypedDict, total=False):
    """State for LangAlpha agent system."""
    # Constants
    TEAM_MEMBERS: List[str]
    
    # Runtime Variables
    messages: List[BaseMessage]
    next: str
    full_plan: str
    final_report: str
    last_agent: Optional[str]
    current_timestamp: Optional[datetime]
    researcher_credits: int
    coder_credits: int
    browser_credits: int
    market_credits: int
    time_range: str
    ticker_type: Optional[Literal["company", "market", "multiple", "ETF", "compare"]]
    tickers: Optional[List[TickerInfo]]
    agent_llm_map: Optional[Dict[str, Any]]
    llm_configs: Optional[Dict[str, Any]]
    
    # Audit and persistence (optional, passed from service layer)
    db: Optional[Any]  # SQLAlchemy Session (not serializable, but used for audit logging)
    user_id: Optional[int]
    analysis_id: Optional[str]


# ============================================================================
# Helper Functions
# ============================================================================


def _get_last_message_content(messages: List) -> str:
    """Get content from the last message; supports BaseMessage (.content) or plain str."""
    if not messages:
        return ""
    last = messages[-1]
    return str(getattr(last, "content", last))


def _get_agent_llm_map(budget_level: str = "medium") -> Dict[str, str]:
    """Get agent LLM mapping based on budget level."""
    budget_level = budget_level.lower()
    
    # Get budget level from settings
    if hasattr(settings, "LANGALPHA_BUDGET_LEVEL"):
        budget_level = settings.LANGALPHA_BUDGET_LEVEL.lower()
    
    if budget_level == "low":
        return {
            "coordinator": "economic",
            "planner": "economic",
            "supervisor": "economic",
            "researcher": "economic",
            "coder": "economic",
            "reporter": "economic",
            "analyst": "economic",
            "browser": "economic",
            "market": "economic",
        }
    elif budget_level == "high":
        return {
            "coordinator": "basic",
            "planner": "reasoning",
            "supervisor": "basic",
            "researcher": "coding",
            "coder": "coding",
            "reporter": "basic",
            "analyst": "basic",
            "browser": "basic",
            "market": "coding",
        }
    else:  # medium (default)
        return {
            "coordinator": "basic",
            "planner": "basic",
            "supervisor": "basic",
            "researcher": "basic",
            "coder": "basic",
            "reporter": "basic",
            "analyst": "basic",
            "browser": "basic",
            "market": "basic",
        }


def _get_llm_by_type(llm_type: str) -> BaseChatModel:
    """Get LLM instance by type using our abstraction."""
    if llm_type == "reasoning":
        model = getattr(settings, "LANGALPHA_REASONING_MODEL", "gpt-4o")
    elif llm_type == "coding":
        model = getattr(settings, "LANGALPHA_CODING_MODEL", "gpt-4o")
    elif llm_type == "economic":
        model = getattr(settings, "LANGALPHA_ECONOMIC_MODEL", "gpt-4o-mini")
    else:  # basic
        model = getattr(settings, "LANGALPHA_BASIC_MODEL", "gpt-4o-mini")
    
    return get_chat_model(temperature=0.7 if llm_type == "reasoning" else 0.0)


def _load_prompt_template(agent_name: str, state: State) -> str:
    """Load prompt template for an agent."""
    prompt_file = PROMPTS_DIR / f"{agent_name}.md"
    
    if not prompt_file.exists():
        logger.warning(f"Prompt file not found: {prompt_file}, using default")
        return f"You are a {agent_name} agent. Complete the task assigned to you."
    
    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            template = f.read()
        
        # Replace template variables
        template = template.replace("<<CURRENT_TIME>>", str(state.get("current_timestamp", datetime.now())))
        template = template.replace("<<TEAM_MEMBERS>>", ", ".join(state.get("TEAM_MEMBERS", TEAM_MEMBERS)))
        template = template.replace("<<time_range>>", state.get("time_range", "not specified"))
        template = template.replace("<<researcher_credits>>", str(state.get("researcher_credits", 0)))
        template = template.replace("<<coder_credits>>", str(state.get("coder_credits", 0)))
        template = template.replace("<<browser_credits>>", str(state.get("browser_credits", 0)))
        template = template.replace("<<market_credits>>", str(state.get("market_credits", 0)))
        
        return template
    except Exception as e:
        logger.error(f"Error loading prompt template for {agent_name}: {e}")
        return f"You are a {agent_name} agent. Complete the task assigned to you."


# ============================================================================
# Node Functions
# ============================================================================

async def coordinator_node(state: State) -> Command[Literal["planner", "__end__"]]:
    """Coordinator node that handles initial user interaction."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    coordinator_llm_type = agent_llm_map.get("coordinator", "basic")
    
    llm = _get_llm_by_type(coordinator_llm_type)
    
    # Load coordinator prompt
    prompt = _load_prompt_template("coordinator", state)
    
    # Get user message
    user_message = ""
    if state.get("messages"):
        last_msg = state["messages"][-1]
        if isinstance(last_msg, HumanMessage):
            user_message = last_msg.content
        elif isinstance(last_msg, str):
            user_message = last_msg
    
    # For now, always hand off to planner
    # TODO: Implement structured output for CoordinatorInstructions
    goto = "planner"
    
    # Audit log state transition
    db = state.get("db")
    user_id = state.get("user_id")
    analysis_id = state.get("analysis_id")
    if db and user_id and analysis_id:
        try:
            log_audit_action(
                db=db,
                action=AuditAction.UPDATE,
                target_type="agent_state_transition",
                target_id=None,  # analysis_id is string, not int
                user_id=user_id,
                metadata={
                    "from": "coordinator",
                    "to": "planner",
                    "analysis_id": analysis_id,
                    "current_step": "coordinator"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log state transition: {e}")
    
    return Command(
        update={
            "last_agent": "coordinator",
            "next": goto,
            "time_range": state.get("time_range", "not specified"),
            "ticker_type": state.get("ticker_type"),
            "tickers": state.get("tickers"),
        },
        goto=goto,
    )


async def planner_node(state: State) -> Command[Literal["supervisor", "__end__"]]:
    """Planner node that generates the full plan."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    planner_llm_type = agent_llm_map.get("planner", "basic")
    
    llm = _get_llm_by_type(planner_llm_type)
    
    # Load planner prompt
    prompt = _load_prompt_template("planner", state)
    
    # Get conversation context
    messages = state.get("messages", [])
    
    # Invoke LLM to generate plan
    response = await llm.ainvoke([HumanMessage(content=prompt + "\n\nUser query: " + _get_last_message_content(messages))])
    
    plan_content = response.content if hasattr(response, 'content') else str(response)
    
    goto = "supervisor"
    
    # Audit log state transition
    db = state.get("db")
    user_id = state.get("user_id")
    analysis_id = state.get("analysis_id")
    if db and user_id and analysis_id:
        try:
            log_audit_action(
                db=db,
                action=AuditAction.UPDATE,
                target_type="agent_state_transition",
                target_id=None,
                user_id=user_id,
                metadata={
                    "from": "planner",
                    "to": "supervisor",
                    "analysis_id": analysis_id,
                    "current_step": "planner"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to log state transition: {e}")
    
    return Command(
        update={
            "next": goto,
            "messages": [HumanMessage(content=plan_content, name="planner")],
            "full_plan": plan_content,
            "last_agent": "planner"
        },
        goto=goto,
    )


async def supervisor_node(state: State) -> Command[Literal["researcher", "coder", "reporter", "market", "browser", "analyst", "__end__"]]:
    """Supervisor node that decides which agent should act next."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    supervisor_llm_type = agent_llm_map.get("supervisor", "basic")
    
    llm = _get_llm_by_type(supervisor_llm_type)
    
    # Load supervisor prompt
    prompt = _load_prompt_template("supervisor", state)
    
    # Get conversation context
    messages = state.get("messages", [])
    
    # Invoke LLM to decide next agent
    response = await llm.ainvoke([HumanMessage(content=prompt + "\n\nContext: " + _get_last_message_content(messages))])
    
    # Parse response to determine next agent
    # TODO: Use structured output for SupervisorInstructions
    response_text = response.content if hasattr(response, 'content') else str(response)
    
    # Simple routing logic (will be improved with structured output)
    goto: str = "__end__"
    if "researcher" in response_text.lower():
        goto = "researcher"
    elif "market" in response_text.lower():
        goto = "market"
    elif "analyst" in response_text.lower():
        goto = "analyst"
    elif "reporter" in response_text.lower():
        goto = "reporter"
    elif "coder" in response_text.lower():
        goto = "coder"
    elif "browser" in response_text.lower():
        goto = "browser"
    
    return Command(
        update={
            "next": goto,
            "messages": [HumanMessage(content=response_text, name="supervisor")],
            "last_agent": "supervisor"
        },
        goto=goto,
    )


async def research_node(state: State) -> Command[Literal["supervisor"]]:
    """Research node that performs research tasks."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    researcher_llm_type = agent_llm_map.get("researcher", "basic")
    
    llm = _get_llm_by_type(researcher_llm_type)
    
    # Set audit context for tools
    set_audit_context(
        db=state.get("db"),
        user_id=state.get("user_id"),
        analysis_id=state.get("analysis_id")
    )
    
    # Create tools for researcher
    tools = [web_search, get_tickertick_news]
    
    # Create ReAct agent
    agent = create_react_agent(llm, tools)
    
    # Load researcher prompt
    prompt = _load_prompt_template("researcher", state)
    
    # Get task from supervisor
    messages = state.get("messages", [])
    task_message = HumanMessage(content=prompt + "\n\nTask: " + _get_last_message_content(messages))
    
    # Execute agent
    result = await agent.ainvoke({"messages": [task_message]})
    
    # Update credits
    researcher_credits = state.get("researcher_credits", 0)
    researcher_credits = max(0, researcher_credits - 1)
    
    response_content = result.get("messages", [AIMessage(content="Research completed")])[-1].content
    
    return Command(
        update={
            "messages": [HumanMessage(content=response_content, name="researcher")],
            "last_agent": "researcher",
            "researcher_credits": researcher_credits,
            "next": "supervisor"
        },
        goto="supervisor",
    )


async def market_node(state: State) -> Command[Literal["supervisor"]]:
    """Market node that performs market analysis tasks."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    market_llm_type = agent_llm_map.get("market", "basic")
    
    llm = _get_llm_by_type(market_llm_type)
    
    # Set audit context for tools
    set_audit_context(
        db=state.get("db"),
        user_id=state.get("user_id"),
        analysis_id=state.get("analysis_id")
    )
    
    # Create tools for market agent
    tools = [get_market_data, get_ticker_snapshot, get_fundamental_data, get_trading_signals]
    
    # Create ReAct agent
    agent = create_react_agent(llm, tools)
    
    # Load market prompt
    prompt = _load_prompt_template("market", state)
    
    # Get task from supervisor
    messages = state.get("messages", [])
    task_message = HumanMessage(content=prompt + "\n\nTask: " + _get_last_message_content(messages))
    
    # Execute agent
    result = await agent.ainvoke({"messages": [task_message]})
    
    # Update credits
    market_credits = state.get("market_credits", 0)
    market_credits = max(0, market_credits - 1)
    
    response_content = result.get("messages", [AIMessage(content="Market analysis completed")])[-1].content
    
    return Command(
        update={
            "messages": [HumanMessage(content=response_content, name="market")],
            "last_agent": "market",
            "market_credits": market_credits,
            "next": "supervisor"
        },
        goto="supervisor",
    )


async def analyst_node(state: State) -> Command[Literal["supervisor"]]:
    """Analyst node that generates financial analysis."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    analyst_llm_type = agent_llm_map.get("analyst", "basic")
    
    llm = _get_llm_by_type(analyst_llm_type)
    
    # Load analyst prompt
    prompt = _load_prompt_template("analyst", state)
    
    # Get conversation context
    messages = state.get("messages", [])
    
    # Invoke LLM to generate analysis
    response = await llm.ainvoke([HumanMessage(content=prompt + "\n\nContext: " + _get_last_message_content(messages))])
    
    analysis_content = response.content if hasattr(response, 'content') else str(response)
    
    return Command(
        update={
            "next": "supervisor",
            "messages": [HumanMessage(content=analysis_content, name="analyst")],
            "last_agent": "analyst"
        },
        goto="supervisor",
    )


async def reporter_node(state: State) -> Command[Literal["__end__"]]:
    """Reporter node that writes a final report."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    reporter_llm_type = agent_llm_map.get("reporter", "basic")
    
    llm = _get_llm_by_type(reporter_llm_type)
    
    # Load reporter prompt
    prompt = _load_prompt_template("reporter", state)
    
    # Get conversation context
    messages = state.get("messages", [])
    
    # Invoke LLM to generate report
    response = await llm.ainvoke([HumanMessage(content=prompt + "\n\nContext: " + _get_last_message_content(messages))])
    
    report_content = response.content if hasattr(response, 'content') else str(response)
    
    return Command(
        update={
            "messages": [AIMessage(content="Reporter has finished the task.", name="reporter")],
            "final_report": report_content,
        },
        goto="__end__",
    )


async def coder_node(state: State) -> Command[Literal["supervisor"]]:
    """Coder node that executes Python code."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    coder_llm_type = agent_llm_map.get("coder", "coding")
    
    llm = _get_llm_by_type(coder_llm_type)
    
    # Set audit context for tools
    set_audit_context(
        db=state.get("db"),
        user_id=state.get("user_id"),
        analysis_id=state.get("analysis_id")
    )
    
    # Create tools for coder
    tools = [python_repl_tool]
    
    # Create ReAct agent
    agent = create_react_agent(llm, tools)
    
    # Load coder prompt
    prompt = _load_prompt_template("coder", state)
    
    # Get task from supervisor
    messages = state.get("messages", [])
    task_message = HumanMessage(content=prompt + "\n\nTask: " + _get_last_message_content(messages))
    
    # Execute agent
    result = await agent.ainvoke({"messages": [task_message]})
    
    # Update credits
    coder_credits = state.get("coder_credits", 0)
    coder_credits = max(0, coder_credits - 1)
    
    response_content = result.get("messages", [AIMessage(content="Code execution completed")])[-1].content
    
    return Command(
        update={
            "messages": [HumanMessage(content=response_content, name="coder")],
            "last_agent": "coder",
            "coder_credits": coder_credits,
            "next": "supervisor"
        },
        goto="supervisor",
    )


async def browser_node(state: State) -> Command[Literal["supervisor"]]:
    """Browser node that performs web browsing tasks."""
    agent_llm_map = state.get("agent_llm_map") or _get_agent_llm_map()
    browser_llm_type = agent_llm_map.get("browser", "basic")
    
    llm = _get_llm_by_type(browser_llm_type)
    
    # Create tools for browser
    tools = [browser_tool]
    
    # Create ReAct agent
    agent = create_react_agent(llm, tools)
    
    # Load browser prompt
    prompt = _load_prompt_template("browser", state)
    
    # Get task from supervisor
    messages = state.get("messages", [])
    task_message = HumanMessage(content=prompt + "\n\nTask: " + _get_last_message_content(messages))
    
    # Execute agent
    result = await agent.ainvoke({"messages": [task_message]})
    
    # Update credits
    browser_credits = state.get("browser_credits", 0)
    browser_credits = max(0, browser_credits - 1)
    
    response_content = result.get("messages", [AIMessage(content="Browser task completed")])[-1].content
    
    return Command(
        update={
            "messages": [HumanMessage(content=response_content, name="browser")],
            "last_agent": "browser",
            "browser_credits": browser_credits,
            "next": "supervisor"
        },
        goto="supervisor",
    )


# ============================================================================
# Graph Builder
# ============================================================================

def build_langalpha_graph(checkpointing_enabled: bool = True) -> StateGraph:
    """
    Build and return the LangAlpha agent workflow graph.
    
    Args:
        checkpointing_enabled: Whether to enable checkpointing for long-running analyses
        
    Returns:
        Compiled StateGraph with optional checkpointing
    """
    workflow = StateGraph(State)
    
    # Add nodes
    workflow.add_node("coordinator", coordinator_node)
    workflow.add_node("planner", planner_node)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("researcher", research_node)
    workflow.add_node("market", market_node)
    workflow.add_node("analyst", analyst_node)
    workflow.add_node("reporter", reporter_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("browser", browser_node)
    
    # Define edges
    workflow.set_entry_point("coordinator")
    workflow.add_edge("coordinator", "planner")
    workflow.add_edge("planner", "supervisor")
    
    # Supervisor routes to agents
    workflow.add_conditional_edges(
        "supervisor",
        lambda state: state.get("next", "__end__"),
        {
            "researcher": "researcher",
            "market": "market",
            "analyst": "analyst",
            "reporter": "reporter",
            "coder": "coder",
            "browser": "browser",
            "__end__": END,
        }
    )
    
    # All agents return to supervisor
    workflow.add_edge("researcher", "supervisor")
    workflow.add_edge("market", "supervisor")
    workflow.add_edge("analyst", "supervisor")
    workflow.add_edge("coder", "supervisor")
    workflow.add_edge("browser", "supervisor")
    
    # Reporter ends the workflow
    workflow.add_edge("reporter", END)
    
    # Compile with optional checkpointing
    if checkpointing_enabled:
        try:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
            return workflow.compile(checkpointer=checkpointer)
        except ImportError:
            logger.warning("LangGraph checkpointing not available, compiling without checkpointing")
            return workflow.compile()
    else:
        return workflow.compile()
