from app.graph.state import NetworkDesignState
from app.utils.llm import get_llm_response
from typing import Dict, Any
import json

def planning_node(state: NetworkDesignState) -> Dict[str, Any]:
    """
    Planning Agent: Analyzes user input and asks clarifying questions.
    """
    
    user_input = state["user_input"]
    history = state.get("conversation_history", [])
    
    # Build context for LLM
    if not history:
        # First interaction
        prompt = f"""You are a network design planning agent.

User request: "{user_input}"

Analyze this request and determine if you have enough information to create a network design.

Required information:
- Number of sites/offices/locations
- Number of users per site
- Connectivity requirements (internet, VPN, inter-site)
- Routing protocol preference (or recommend if unsure)
- Security requirements (firewall, VLANs, etc.)
- Any special services (web servers, databases, etc.)

If ANY required information is missing, output:
{{
  "requirements_clear": false,
  "clarifying_questions": ["question 1", "question 2", ...]
}}

If ALL information is present, output:
{{
  "requirements_clear": true,
  "design_plan": {{
    "sites": [...],
    "users_per_site": X,
    "protocols": ["ospf"],
    "security": ["firewall", "vlans"],
    ...
  }}
}}

Output ONLY valid JSON, no other text.
"""
    else:
        # Follow-up: user has answered questions
        conversation_text = "\n".join([
            f"Assistant: {msg.get('content', '')}" if msg.get('role') == 'assistant' else f"User: {msg.get('content', '')}"
            for msg in history
        ])
        
        prompt = f"""You are a network design planning agent.

Previous conversation:
{conversation_text}

Latest user input: "{user_input}"

Based on the complete conversation, do you now have enough information?

Required information:
- Number of sites/offices/locations
- Number of users per site
- Connectivity requirements
- Routing protocols
- Security requirements

If still missing information, output:
{{
  "requirements_clear": false,
  "clarifying_questions": ["specific question about missing info"]
}}

If complete, output:
{{
  "requirements_clear": true,
  "design_plan": {{
    "sites": [...],
    "users_per_site": X,
    "protocols": ["ospf"],
    ...
  }}
}}

Output ONLY valid JSON.
"""
    
    # Call LLM (Groq)
    try:
        response_text = get_llm_response(prompt, model="llama-3.3-70b-versatile")
        
        # Parse response
        try:
            # Clean markdown
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            response_json = json.loads(clean_text)
        except json.JSONDecodeError:
            # Fallback: treat as needing clarification
            return {
                "requirements_clear": False,
                "clarifying_questions": ["Could you provide more details about your network requirements?"],
                "conversation_history": [{"role": "assistant", "content": "I need more information (JSON Parse Error)."}]
            }
            
    except Exception as e:
        # Graceful fallback for LLM/Network errors
        print(f"LLM Error: {str(e)}")
        return {
            "requirements_clear": False,
            "clarifying_questions": [f"I encountered an error connecting to the AI service: {str(e)}. Please try again."],
            "conversation_history": [{"role": "assistant", "content": f"Error: {str(e)}"}]
        }
    
    # Update state
    updates = {
        "requirements_clear": response_json.get("requirements_clear", False),
        "conversation_history": [{"role": "assistant", "content": response_text}]
    }
    
    if response_json.get("requirements_clear"):
        updates["design_plan"] = response_json.get("design_plan")
    else:
        updates["clarifying_questions"] = response_json.get("clarifying_questions", [])
    
    return updates
