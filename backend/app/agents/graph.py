import time

from langgraph.graph import END, START, StateGraph

from app.agents.critic import critic
from app.agents.llm import get_fallback_events, get_token_usage, reset_token_usage
from app.agents.planner import planner
from app.agents.query_clarifier import query_clarifier
from app.agents.retriever_agent import retriever_agent
from app.agents.state import AgentState, initial_state
from app.agents.synthesizer import synthesizer
from app.observability.tracing import observe


def _route_after_clarifier(state: AgentState) -> str:
    return "guardrail_block" if state.get("blocked") else "planner"


def _route_after_critic(state: AgentState) -> str:
    return "retriever" if state.get("needs_re_retrieval") else END


async def _blocked_node(state: AgentState) -> dict:
    # Terminal node when guardrails reject the input.
    return {}


def build_agent_graph():
    graph = StateGraph(AgentState)

    graph.add_node("query_clarifier", query_clarifier)
    graph.add_node("planner", planner)
    graph.add_node("retriever", retriever_agent)
    graph.add_node("synthesizer", synthesizer)
    graph.add_node("critic", critic)
    graph.add_node("guardrail_block", _blocked_node)

    graph.add_edge(START, "query_clarifier")
    graph.add_conditional_edges(
        "query_clarifier",
        _route_after_clarifier,
        {"guardrail_block": "guardrail_block", "planner": "planner"},
    )
    graph.add_edge("guardrail_block", END)
    graph.add_edge("planner", "retriever")
    graph.add_edge("retriever", "synthesizer")
    graph.add_edge("synthesizer", "critic")
    graph.add_conditional_edges("critic", _route_after_critic, {"retriever": "retriever", END: END})

    return graph.compile()


agent_pipeline = build_agent_graph()


@observe(name="agentic_rag_pipeline")
async def run_pipeline(
    question: str,
    conversation_history: list[dict] | None = None,
    document_ids: list[str] | None = None,
) -> dict:
    """Run the full multi-agent pipeline and return the final state enriched with
    latency and token usage (for cost tracking / the trace viewer)."""
    reset_token_usage()
    start = time.perf_counter()
    final_state = await agent_pipeline.ainvoke(
        initial_state(question, conversation_history, document_ids)
    )
    latency_ms = round((time.perf_counter() - start) * 1000, 1)

    usage = get_token_usage()
    final_state["latency_ms"] = latency_ms
    final_state["token_usage"] = usage
    final_state["model_fallbacks"] = get_fallback_events()
    return final_state
