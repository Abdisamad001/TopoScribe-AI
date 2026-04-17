from langgraph.graph import StateGraph, END
from app.graph.state import NetworkDesignState
from app.agents.planning_agent import planning_node
from app.agents.topology_agent import topology_node
from app.agents.config_agent import config_node
from app.agents.validation_agent import validation_node

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


def should_end_or_continue(state: NetworkDesignState) -> str:
    """
    Checks if there are errors after validation.
    
    Returns:
        - "end" → Success, output ready
        - "config" → Errors found, retry configuration
    """
    validation = state.get("validation_result") or {}
    if isinstance(validation, dict) and validation.get("status") == "failed_fatal":
        return "end"
    errors = state.get("errors", [])
    if errors:
        return "config"  # Retry
    return "end"


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

# Linear flow after planning
workflow.add_edge("topology_gen", "config")
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
