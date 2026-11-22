from typing import TypedDict, List, Optional, Annotated
from app.models.network import Topology
import operator

class NetworkDesignState(TypedDict):
    # User interaction
    user_input: str                                      # Original request
    # Full chat history
    conversation_history: Annotated[List[dict], operator.add]  
    
    # Planning phase
    requirements_clear: bool                            
    clarifying_questions: Optional[List[str]]        
    design_plan: Optional[dict]                          
    
    # Generation phases
    topology: Optional[Topology]                       
    topology_retry_count: int                            # Topology attempts after first
    topology_source: Optional[str]                       # groq , openai_escalated ,deterministic_fallback
    topology_quality_ok: bool                           
    configurations: Optional[dict]                       
    validation_result: Optional[dict]                    
    
    # Final output
    cisco_configs: Optional[dict]                     
    report: Optional[str]                               
    
    # Error handling
    errors: Annotated[List[str], operator.add]         
    retry_count: int                                  

    # Observability
    agent_trace: Annotated[List[dict], operator.add]   
