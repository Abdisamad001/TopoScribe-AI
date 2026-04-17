from app.graph.state import NetworkDesignState
from app.utils.llm import get_llm_response
from typing import Dict, Any, List
import json
import re


def _extract_department_names(text: str) -> List[str]:
    """
    Heuristic extraction of department names from free text.
    Supports patterns like:
    - departments: HR, IT, Finance
    - department HR, IT and Finance
    """
    if not text:
        return []
    m = re.search(r"departments?\s*[:\-]?\s*([^\n\.]+)", text, flags=re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1)
    parts = re.split(r",|\band\b|/|\|", raw, flags=re.IGNORECASE)
    out: List[str] = []
    for p in parts:
        name = p.strip(" \"'[](){}")
        if name:
            out.append(name)
    # Deduplicate while preserving order
    seen = set()
    uniq: List[str] = []
    for n in out:
        k = n.lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(n)
    return uniq


def _apply_sme_defaults(plan: Dict[str, Any], user_input: str, history: List[dict]) -> Dict[str, Any]:
    """
    Enforce SME campus defaults and keep scope to Cisco 1941 + 2960, IPv4, VLAN, OSPF area 0.
    """
    p = dict(plan or {})
    all_text = " ".join(
        [user_input or ""] + [str((m or {}).get("content", "")) for m in (history or [])]
    )

    # Sites default
    sites = p.get("sites")
    if not isinstance(sites, list) or not sites:
        p["sites"] = ["Main Site"]

    # Department defaults if missing users/vlan_id
    depts = p.get("departments")
    if isinstance(depts, list):
        normalized = []
        for i, d in enumerate(depts):
            if not isinstance(d, dict):
                continue
            name = str(d.get("name") or d.get("department") or f"Department {i + 1}")
            users = d.get("users", 20)
            try:
                users_i = int(users)
            except (TypeError, ValueError):
                users_i = 20
            vlan_id = d.get("vlan_id")
            try:
                vlan_i = int(vlan_id) if vlan_id is not None else (10 * (i + 1))
            except (TypeError, ValueError):
                vlan_i = 10 * (i + 1)
            normalized.append({"name": name, "users": users_i, "vlan_id": vlan_i})
        p["departments"] = normalized
    else:
        p["departments"] = []

    # If LLM missed departments but user listed them explicitly, infer them.
    if not p["departments"]:
        inferred = _extract_department_names(all_text)
        if inferred:
            p["departments"] = [
                {"name": n, "users": 20, "vlan_id": 10 * (i + 1)} for i, n in enumerate(inferred)
            ]

    # VLAN catalog (always mirror departments)
    p["vlans"] = [{"id": int(d["vlan_id"]), "name": str(d["name"])} for d in p["departments"]]

    # Fixed SME defaults/scope
    p["users_per_site"] = p.get("users_per_site", 20)
    p["protocols"] = ["ospf"]
    p["ospf"] = {"area": 0}
    p["connectivity"] = p.get("connectivity", "Internal campus connectivity with internet gateway")
    p["security"] = ["vlans"]
    p["devices"] = {
        "router": "Cisco 1941",
        "switch": "Catalyst 2960",
        "addressing": "IPv4 private",
    }

    # Remove out-of-scope fields if present
    p.pop("vpn", None)
    p.pop("firewall", None)
    p.pop("services", None)
    p.pop("external_services", None)
    return p


def _is_user_delegation(user_input: str, history: List[dict]) -> bool:
    """
    True when user explicitly delegates technical decisions to the system.
    """
    text = " ".join(
        [user_input or ""] + [str((m or {}).get("content", "")) for m in (history or [])]
    ).lower()
    delegation_patterns = [
        r"\brecommend\b",
        r"\bsuggest\b",
        r"\bdecide\b",
        r"\byou choose\b",
        r"\bchoose for me\b",
    ]
    return any(re.search(p, text) for p in delegation_patterns)


def _ensure_default_departments(plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    If departments are absent, inject SME baseline departments for delegated requests.
    """
    p = dict(plan or {})
    depts = p.get("departments")
    if isinstance(depts, list) and depts:
        return p
    p["departments"] = [
        {"name": "HR", "users": 20, "vlan_id": 10},
        {"name": "IT", "users": 20, "vlan_id": 20},
        {"name": "Finance", "users": 20, "vlan_id": 30},
    ]
    p["vlans"] = [{"id": int(d["vlan_id"]), "name": str(d["name"])} for d in p["departments"]]
    return p

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
   - Missing departments/organizational VLAN groups.
2) Inference gaps (DO NOT ask):
   - sites, users, connectivity, protocols, vlan ids.
   Infer with SME defaults.
3) If departments are provided, set requirements_clear=true immediately.
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
        delegated = _is_user_delegation(user_input, history)
        if delegated:
            plan = _apply_sme_defaults({}, user_input, history)
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
    if delegated:
        plan = _ensure_default_departments(plan)
    has_departments = bool(plan.get("departments"))

    # Enforce fatal-gap behavior: only departments can block progression.
    requirements_clear = bool(response_json.get("requirements_clear", False)) and has_departments
    if delegated:
        requirements_clear = True
    if has_departments:
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
