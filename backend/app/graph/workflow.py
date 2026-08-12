from langgraph.graph import StateGraph, END
from app.graph.state import NetworkDesignState
from app.agents.planning_agent import planning_node
from app.agents.topology_agent import topology_node, MAX_TOPOLOGY_RETRIES
from app.agents.config_agent import config_node
from app.agents.validation_agent import validation_node

# Validation->config cycles allowed before the graph gives up and returns the
# accumulated errors, instead of looping until LangGraph's recursion limit.
MAX_VALIDATION_RETRIES = 3

# ============================================================
# CONDITIONAL ROUTING FUNCTIONS
# ============================================================

def should_continue_planning(state: NetworkDesignState) -> str:
    """
    Determines if Planning Agent needs more information.
    
    Returns:
        - "ask_user" → Stop graph, return questions to user
        - "topology_gen" → Requirements clear, proceed to Topology Agent
    """
    if state.get("requirements_clear", False):
        return "topology_gen"
    else:
        return "ask_user"


def should_retry_topology(state: NetworkDesignState) -> str:
    """
    Decides what happens after the Topology Agent runs.

    Returns:
        - "config" → a topology exists (LLM output or deterministic fallback), proceed
        - "topology_gen" → rejected by the quality gate, run another (escalated) attempt
        - "end_failed" → the agent exhausted its budget and the fallback itself threw

    The attempt budget lives in topology_node (topology_retry_count), so this
    router owns no counter of its own — it only reads the node's counter to
    recognise the exhausted case, which is the one state that must not loop.
    """
    if state.get("topology") is not None:
        return "config"
    if int(state.get("topology_retry_count", 0) or 0) > MAX_TOPOLOGY_RETRIES:
        return "end_failed"
    if not state.get("topology_quality_ok", True):
        return "topology_gen"
    return "end_failed"


def should_end_or_continue(state: NetworkDesignState) -> str:
    """
    Checks if there are errors after validation.
    
    Returns:
        - "end" → Success, fatal gap, or retry budget exhausted; output ready
        - "config" → Errors found, retry configuration
    """
    validation = state.get("validation_result") or {}
    if isinstance(validation, dict) and validation.get("status") == "failed_fatal":
        return "end"
    errors = state.get("errors", [])
    if not errors:
        return "end"
    # validation_node increments retry_count on every failed pass, so this
    # allows MAX_VALIDATION_RETRIES trips back to config and then stops with
    # the accumulated errors rather than spinning to the recursion limit.
    if int(state.get("retry_count", 0) or 0) > MAX_VALIDATION_RETRIES:
        return "end"
    return "config"  # Retry


# ============================================================
# BUILD THE GRAPH
# ============================================================

workflow = StateGraph(NetworkDesignState)

# Add agent nodes
workflow.add_node("planning", planning_node)
workflow.add_node("topology_gen", topology_node)
workflow.add_node("config", config_node)
workflow.add_node("validation", validation_node)

# Set entry point
workflow.set_entry_point("planning")

# CRITICAL: Conditional edge from planning
# This creates the loop: planning → planning (if unclear) OR planning → topology (if clear)
workflow.add_conditional_edges(
    "planning",
    should_continue_planning,
    {
        "ask_user": END,    # STOP graph, return to user
        "topology_gen": "topology_gen"      # PROCEED to next agent
    }
)

# Topology quality gate: retry (escalated) until the output passes or the
# agent's own budget is spent.
workflow.add_conditional_edges(
    "topology_gen",
    should_retry_topology,
    {
        "config": "config",                 # Usable topology, continue
        "topology_gen": "topology_gen",     # Rejected, try again on a stronger model
        "end_failed": END,                  # Budget spent and fallback unavailable
    }
)

workflow.add_edge("config", "validation")

# Optional: Add retry logic after validation
workflow.add_conditional_edges(
    "validation",
    should_end_or_continue,
    {
        "config": "config",  # Retry if errors
        "end": END           # Success
    }
)

# Compile the graph
app = workflow.compile()
