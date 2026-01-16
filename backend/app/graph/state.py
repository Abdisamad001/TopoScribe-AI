from typing import TypedDict, List, Optional, Annotated
from app.models.network import Topology
import operator

class NetworkDesignState(TypedDict):
    # User interaction
    user_input: str                                      # Original request
    conversation_history: Annotated[List[dict], operator.add]  # Full chat history
    
    # Planning phase
    requirements_clear: bool                             # True when all info collected
    clarifying_questions: Optional[List[str]]            # Questions to ask user
    design_plan: Optional[dict]                          # Structured plan after clarification
    
    # Generation phases
    topology: Optional[Topology]                         # Generated network topology
    configurations: Optional[dict]                       # Device configurations
    validation_result: Optional[dict]                    # Validation report
    
    # Final output
    cisco_configs: Optional[dict]                        # Per-device Cisco CLI configs
    report: Optional[str]                                # Human-readable report
    
    # Error handling
    errors: Annotated[List[str], operator.add]          # Accumulated errors
