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
    if state.get("requirements_clear", False):
        return "topology_gen"
    else:
        return "ask_user"


def should_retry_topology(state: NetworkDesignState) -> str:
    if state.get("topology") is not None:
        return "config"
    if int(state.get("topology_retry_count", 0) or 0) > MAX_TOPOLOGY_RETRIES:
        return "end_failed"
    if not state.get("topology_quality_ok", True):
        return "topology_gen"
    return "end_failed"


def should_end_or_continue(state: NetworkDesignState) -> str:
    validation = state.get("validation_result") or {}
    if isinstance(validation, dict) and validation.get("status") == "failed_fatal":
        return "end"
    errors = state.get("errors", [])
    if not errors:
        return "end"
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

# Conditional edge from planning
workflow.add_conditional_edges(
    "planning",
    should_continue_planning,
    {
        "ask_user": END,    
        "topology_gen": "topology_gen"      
    }
)

# Topology Escalation
workflow.add_conditional_edges(
    "topology_gen",
    should_retry_topology,
    {
        "config": "config",                 
        "topology_gen": "topology_gen",    
        "end_failed": END,                  
    }
)

workflow.add_edge("config", "validation")

# retry logic after validation
workflow.add_conditional_edges(
    "validation",
    should_end_or_continue,
    {
        "config": "config",  
        "end": END          
    }
)


app = workflow.compile()
