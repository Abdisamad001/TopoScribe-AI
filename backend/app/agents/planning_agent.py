from app.graph.state import NetworkDesignState
from app.utils.llm import call_llm
from app.utils.dept_labels import (
    filter_department_string_list,
    is_plausible_department_name,
    sanitize_department_name,
)
from typing import Dict, Any, List
import json
import re


def _infer_departments_from_free_text(text: str) -> List[str]:
    """
    Extract department names without requiring 'departments:' prefix.
    Handles e.g. 'two departments IT, CS, 2 sites', 'IT and CS', 'department IT, Finance'.
    """
    if not text:
        return []
    t = text.strip()
    candidates: List[str] = []

    # Strong pattern: "... departments IT, CS, 2 sites ..." (capture may include commas)
    m = re.search(
        r"departments?\s+(.+?)\s*,\s*\d+\s+sites?\b",
        t,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if m:
        raw = m.group(1)
        for part in re.split(r",|\band\b|/|\|", raw):
            n = part.strip().strip(" \"'[](){}")
            if n and len(n) <= 64 and not re.fullmatch(r"\d+", n):
                if n.lower() not in ("vlan", "each", "users", "user"):
                    candidates.append(n)

    # "... departments IT, CS, ... 2 sites ..." (common user phrasing)
    if not candidates:
        m = re.search(
            r"departments?\s+(.+?)(?:,\s*\d+\s+sites\b|\s+sites\b\s+in\b|,?\s*\d+\s+sites\b|\s+with\b|\.\s*$|$)",
            t,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if m:
            raw = m.group(1)
            for part in re.split(r",|\band\b|/|\|", raw):
                n = part.strip().strip(" \"'[](){}")
                n = re.split(r"\s+with\s+", n, maxsplit=1, flags=re.IGNORECASE)[0].strip()
                if not n or len(n) > 64:
                    continue
                if re.fullmatch(r"\d+", n):
                    continue
                low = n.lower()
                if low in ("vlan", "each", "users", "user", "sites", "site", "network", "design"):
                    continue
                candidates.append(n)

    if not candidates:
        m2 = re.search(
            r"(?:one|two|three|four|five|\d+)\s+departments?\s+(.+)",
            t,
            flags=re.IGNORECASE,
        )
        if m2:
            raw = m2.group(1)
            raw = re.split(r",?\s*\d+\s+sites\b", raw, flags=re.IGNORECASE)[0]
            for part in re.split(r",|\band\b|/|\|", raw):
                n = part.strip().strip(" \"'[](){}")
                if not n or len(n) > 64 or re.fullmatch(r"\d+", n):
                    continue
                if n.lower() in ("vlan", "each", "users", "sites", "site"):
                    continue
                candidates.append(n)

    # Short uppercase tokens (IT, CS) — only when few matches to avoid noise
    if not candidates:
        caps = re.findall(r"\b([A-Z]{2,5})\b", t)
        skip = {"VLAN", "LAN", "WAN", "DHCP", "DNS", "TCP", "UDP", "API"}
        for tok in caps:
            if tok in skip:
                continue
            candidates.append(tok)
        if len(candidates) > 6:
            candidates = []

    seen: set = set()
    out: List[str] = []
    for n in candidates:
        k = n.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(n)
    return filter_department_string_list(out[:32])


def _user_messages_text(user_input: str, history: List[dict]) -> str:
    """User-only transcript (excludes assistant text) for inference and delegation."""
    parts = [user_input or ""]
    for m in history or []:
        if (m or {}).get("role") == "user":
            parts.append(str((m or {}).get("content", "")))
    return " ".join(p for p in parts if p).strip()


def _explicit_departments_from_user(user_input: str, history: List[dict]) -> List[str]:
    """Department names the user explicitly named (never from assistant clarifying prompts)."""
    text = _user_messages_text(user_input, history)
    inferred = _extract_department_names(text)
    if not inferred:
        inferred = _infer_departments_from_free_text(text)
    return inferred


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
    return filter_department_string_list(uniq)


def _apply_sme_defaults(plan: Dict[str, Any], user_input: str, history: List[dict]) -> Dict[str, Any]:
    """
    Enforce SME campus defaults and keep scope to Cisco 1941 + 2960, IPv4, VLAN, OSPF area 0.
    """
    p = dict(plan or {})
    user_text = _user_messages_text(user_input, history)
    explicit_depts = _explicit_departments_from_user(user_input, history)

    # Sites default — honor "N sites" in user text when present
    sites = p.get("sites")
    if not isinstance(sites, list) or not sites:
        sm = re.search(
            r"\b(\d+)\s+sites?\b",
            user_text,
            flags=re.IGNORECASE,
        )
        if sm:
            try:
                n_sites = max(1, min(32, int(sm.group(1))))
            except ValueError:
                n_sites = 1
            if n_sites <= 1:
                p["sites"] = ["Main Site"]
            else:
                p["sites"] = [f"Site {i + 1}" for i in range(n_sites)]
        else:
            p["sites"] = ["Main Site"]

    # Department defaults if missing users/vlan_id
    depts = p.get("departments")
    if isinstance(depts, list):
        normalized = []
        for i, d in enumerate(depts):
            if not isinstance(d, dict):
                continue
            raw_nm = str(d.get("name") or d.get("department") or "")
            name = (
                sanitize_department_name(raw_nm, i)
                if raw_nm
                else sanitize_department_name("", i)
            )
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

    # User-named departments always override LLM/extra defaults.
    if explicit_depts:
        p["departments"] = [
            {"name": n, "users": 20, "vlan_id": 10 * (i + 1)}
            for i, n in enumerate(explicit_depts)
        ]
    elif not p["departments"]:
        inferred = _extract_department_names(user_text)
        if not inferred:
            inferred = _infer_departments_from_free_text(user_text)
        if inferred:
            dedup: List[str] = []
            seen_nm: set = set()
            for n in inferred:
                if not is_plausible_department_name(n):
                    continue
                k = n.strip().lower()
                if k in seen_nm:
                    continue
                seen_nm.add(k)
                dedup.append(n)
            inferred = dedup
            if inferred:
                p["departments"] = [
                    {"name": n, "users": 20, "vlan_id": 10 * (i + 1)}
                    for i, n in enumerate(inferred)
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
    Naming departments explicitly is not delegation of the department set.
    """
    if _explicit_departments_from_user(user_input, history):
        return False
    text = _user_messages_text(user_input, history).lower()
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
    
    # Single call, always the planning tier. The model fixes temperature at 1,
    # so output consistency comes from the strict prompt above plus the
    # deterministic post-processing below, not from a temperature setting.
    try:
        response_text = call_llm(prompt, tier="planning")
        
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
    if delegated and not plan.get("departments"):
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
