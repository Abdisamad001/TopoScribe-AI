from app.graph.state import NetworkDesignState
from app.utils.llm import call_llm
from app.utils.planning_helpers import (
    LITERAL_HOST_NODE_THRESHOLD,
    _apply_sme_defaults,
    _ensure_default_departments,
    _explicit_departments_from_user,
    _extract_department_names,
    _extract_device_inventory,
    _infer_departments_from_free_text,
    _is_flat_inventory_request,
    _is_user_delegation,
    _requested_department_count,
    _requested_literal_hosts_each,
    _requested_users_each,
)
from typing import Dict, Any
import json


def planning_node(state: NetworkDesignState) -> Dict[str, Any]:
    """
    Planning Agent: Analyzes user input and asks clarifying questions.
    """
    
    user_input = state["user_input"]
    history = state.get("conversation_history", [])
    
    conversation_text = "\n".join([
        f"Assistant: {msg.get('content', '')}" if msg.get('role') == 'assistant' else f"User: {msg.get('content', '')}"
        for msg in history
    ])

    prompt = f"""You are the Planning Agent for an SME Campus Network generator.

STRICT SCOPE (do not ask about anything outside this):
- Router: Cisco 1941
- Switches: Catalyst 2960
- Addressing: private IPv4
- Segmentation: VLANs
- Routing: OSPF area 0

Input context:
Previous conversation:
{conversation_text}

Latest user input:
"{user_input}"

Clarification policy:
1) Fatal gaps (ask ONLY these):
   - Missing departments/organizational VLAN groups — BUT only when the request
     implies an organisational / departmental design.
   - If the user stated a complete flat device inventory (explicit counts of
     routers and/or switches plus hosts/PCs/computers) with NO department or
     organisational-unit language, that is NOT a fatal gap. Set
     requirements_clear=true and put mode="flat_inventory" with router_count,
     switch_count, and host_count on the design_plan (departments may be empty).
2) Inference gaps (DO NOT ask):
   - sites, users, connectivity, protocols, vlan ids.
   Infer with SME defaults.
3) If departments are provided, set requirements_clear=true immediately and
   mode="departmental".
   Department scope rule:
   - If the user explicitly names departments, use EXACTLY those departments and NO others — do not add HR, IT, or Finance unless the user named them.
   - If the user did NOT name departments and instead delegated the decision (e.g. said "recommend", "suggest", "you choose", "decide for me"), you MAY apply the default set: HR, IT, Finance.
4) User Delegation override:
   - If user asks you to "recommend", "suggest", or "decide" for them, treat ALL missing
     technical parameters as Approved via Defaults and set requirements_clear=true.
   - Do not ask "Could you provide more details" in this delegation case.

Defaults to apply when missing:
- sites: 1 site
- users per department: 20
- connectivity: internal campus + internet gateway
- protocol: ospf (area 0)
- vlan ids: auto assign 10,20,30...

NEVER ask about VPNs, firewalls, databases, web servers, or external services.

Return ONLY valid JSON:
- If fatal gap exists:
{{
  "requirements_clear": false,
  "clarifying_questions": ["single concise question asking for departments"]
}}
- Otherwise:
{{
  "requirements_clear": true,
  "design_plan": {{
    "sites": ["Main Site"],
    "users_per_site": 20,
    "connectivity": "Internal campus connectivity with internet gateway",
    "protocols": ["ospf"],
    "ospf": {{"area": 0}},
    "departments": [
      {{"name": "HR", "users": 20, "vlan_id": 10}}
    ],
    "vlans": [
      {{"id": 10, "name": "HR"}}
    ],
    "security": ["vlans"],
    "devices": {{
      "router": "Cisco 1941",
      "switch": "Catalyst 2960",
      "addressing": "IPv4 private"
    }}
  }}
}}
"""
    
    # Single call, always the planning tier. Temperature is fixed by the model
    # at 1; consistency comes from the prompt plus deterministic post-processing.
    # reasoning_effort="low" was chosen after a 7-case × 3-repeat comparison vs
    # the gpt-5.5 default (medium): identical correctness, ~58% fewer reasoning
    # tokens and ~29% lower mean wall time. Topology escalation is left at the
    # model default — do not copy this override there without a separate study.
    try:
        response_text = call_llm(prompt, tier="planning", reasoning_effort="low")
        
        # Parse response
        try:
            # Clean markdown
            clean_text = response_text.replace("```json", "").replace("```", "").strip()
            response_json = json.loads(clean_text)
        except json.JSONDecodeError:
            # LLM returned non-JSON — infer departments from user text and proceed with SME defaults
            plan = _apply_sme_defaults({}, user_input, history)
            if not plan.get("departments") and _is_user_delegation(user_input, history):
                plan = _ensure_default_departments(plan)
            return {
                "requirements_clear": True,
                "design_plan": plan,
                "conversation_history": [
                    {
                        "role": "assistant",
                        "content": "Proceeding with SME defaults from your requirements (AI reply was not strict JSON).",
                    }
                ],
            }
            
    except Exception as e:
        # Graceful fallback for LLM/Network errors
        print(f"LLM Error: {str(e)}")
        delegated = _is_user_delegation(user_input, history)
        if delegated:
            plan = _apply_sme_defaults({}, user_input, history)
            if not plan.get("departments"):
                plan = _ensure_default_departments(plan)
            return {
                "requirements_clear": True,
                "design_plan": plan,
                "conversation_history": [
                    {"role": "assistant", "content": "Using SME defaults by delegation."}
                ],
            }
        return {
            "requirements_clear": False,
            "clarifying_questions": [f"I encountered an error connecting to the AI service: {str(e)}. Please try again."],
            "conversation_history": [{"role": "assistant", "content": f"Error: {str(e)}"}]
        }
    
    delegated = _is_user_delegation(user_input, history)
    plan = _apply_sme_defaults(response_json.get("design_plan") or {}, user_input, history)
    if delegated and not plan.get("departments") and plan.get("mode") != "flat_inventory":
        plan = _ensure_default_departments(plan)
        plan["mode"] = "departmental"
    has_departments = bool(plan.get("departments"))
    is_flat = plan.get("mode") == "flat_inventory" and (
        int(plan.get("host_count") or 0) >= 1
        and (
            int(plan.get("router_count") or 0) + int(plan.get("switch_count") or 0) >= 1
        )
    )

    # Fatal-gap: departments block only in departmental mode. Flat inventory is complete
    # once device counts are captured.
    requirements_clear = bool(response_json.get("requirements_clear", False)) and has_departments
    if delegated:
        requirements_clear = True
    if has_departments:
        requirements_clear = True
    if is_flat:
        requirements_clear = True

    updates = {
        "requirements_clear": requirements_clear,
        "conversation_history": [{"role": "assistant", "content": response_text}]
    }

    if requirements_clear:
        updates["design_plan"] = plan
    else:
        updates["clarifying_questions"] = ["Please list your departments (e.g., HR, IT, Finance)."]
    
    return updates
