from app.graph.state import NetworkDesignState
from app.utils.llm import call_llm
from app.utils.dept_labels import (
    filter_department_string_list,
    is_plausible_department_name,
    sanitize_department_name,
)
from typing import Dict, Any, List, Optional
import json
import re


# Small explicit device counts (PCs/hosts) are drawn as real nodes; larger counts
# stay as one representative host per VLAN (users-style sizing).
LITERAL_HOST_NODE_THRESHOLD = 8

# Department words users actually write, so the free-text fallback is not limited
# to bare uppercase acronyms and can see "finance" as readily as "IT".
_DEPARTMENT_VOCABULARY = (
    "accounting", "administration", "admin", "customer service",
    "engineering", "facilities", "finance", "human resources", "hr", "it",
    "legal", "logistics", "maintenance", "manufacturing", "marketing",
    "operations", "ops", "procurement", "production", "purchasing",
    "quality assurance", "qa", "research", "sales", "security", "support",
    "training", "warehouse",
)

# Words that describe the request itself, not an organisational unit. "Design"
# in particular heads almost every prompt this system receives, so it must never
# become a department however it is capitalised.
_NON_DEPARTMENT_WORDS = {
    "design", "network", "networks", "topology", "site", "sites", "office",
    "offices", "campus", "company", "business", "branch", "user", "users",
    "pc", "pcs", "device", "devices", "department", "departments",
}

_DEPARTMENT_ACRONYMS = {"hr", "it", "qa", "ops"}

# Uppercase tokens that are domain vocabulary rather than department names.
_ACRONYM_STOPWORDS = {
    "VLAN", "LAN", "WAN", "DHCP", "DNS", "TCP", "UDP", "API", "IP", "OSPF",
    "SME", "PC", "PCS", "LLM", "AI",
}

_NUMBER_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}

# Order used when a request states how many departments it wants without naming them.
_SME_DEPARTMENT_LADDER = (
    "HR", "IT", "Finance", "Sales", "Operations", "Marketing", "Support", "Legal",
)


def _canonical_department(word: str) -> str:
    """Consistent display casing, without flattening acronyms like 'JS' to 'Js'."""
    w = word.strip()
    low = w.lower()
    if low in _DEPARTMENT_ACRONYMS:
        return low.upper()
    if w.isupper() and len(w) <= 5:
        return w
    if w.islower() or w.isupper():
        return w.title()
    return w


def _named_departments_in_text(text: str) -> List[str]:
    """
    Department names the user actually wrote, in the order written: recognised
    department words in any casing, plus bare acronyms like "JS".
    """
    if not text:
        return []

    found: List[tuple] = []
    vocab = "|".join(
        re.escape(w) for w in sorted(_DEPARTMENT_VOCABULARY, key=len, reverse=True)
    )
    for m in re.finditer(rf"\b({vocab})\b", text, flags=re.IGNORECASE):
        found.append((m.start(), _canonical_department(m.group(1))))

    acronyms = [
        (m.start(), m.group(1))
        for m in re.finditer(r"\b([A-Z]{2,5})\b", text)
        if m.group(1) not in _ACRONYM_STOPWORDS
    ]
    # Prose full of acronyms is noise, not a department list.
    if len(acronyms) <= 6:
        found.extend(acronyms)

    found.sort(key=lambda item: item[0])
    out: List[str] = []
    seen: set = set()
    for _pos, name in found:
        k = name.lower()
        if k in seen or k in _NON_DEPARTMENT_WORDS:
            continue
        seen.add(k)
        out.append(name)
    return out


def _requested_department_count(text: str) -> int:
    """
    How many departments the request asks for by number, e.g. "4-department SME"
    or "four departments". 0 when no count is stated.
    """
    if not text:
        return 0
    m = re.search(
        r"\b(\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")[\s-]+departments?\b",
        text,
        flags=re.IGNORECASE,
    )
    if not m:
        return 0
    token = m.group(1).lower()
    n = _NUMBER_WORDS.get(token)
    if n is None:
        try:
            n = int(token)
        except ValueError:
            return 0
    return n if 1 <= n <= 32 else 0


def _requested_users_each(text: str) -> int:
    """Users per department when the request states one, else 0."""
    m = re.search(r"\b(\d{1,4})\s+users?\b", text or "", flags=re.IGNORECASE)
    if not m:
        return 0
    try:
        n = int(m.group(1))
    except ValueError:
        return 0
    return n if 1 <= n <= 10000 else 0


_COUNT_TOKEN = (
    r"(?P<n>\d{1,4}|a|an|" + "|".join(_NUMBER_WORDS) + r")"
)
_HOST_DEVICE_WORDS = (
    r"(?:pcs?|computers?|hosts?|laptops?|workstations?|end[- ]?devices?)"
)


def _parse_count_token(token: str) -> int:
    """Digits, number-words, or a/an → positive int; 0 if unusable."""
    t = (token or "").strip().lower()
    if t in ("a", "an"):
        return 1
    if t in _NUMBER_WORDS:
        return _NUMBER_WORDS[t]
    try:
        n = int(t)
    except ValueError:
        return 0
    return n if 1 <= n <= 10000 else 0


def _sum_device_role_counts(text: str, role_pattern: str) -> Optional[int]:
    """
    Sum every explicit count for a device role in free text.
    None when the role is never mentioned (distinct from an explicit zero).
    """
    if not text:
        return None
    total = 0
    found = False
    for m in re.finditer(
        rf"\b{_COUNT_TOKEN}\s+{role_pattern}\b",
        text,
        flags=re.IGNORECASE,
    ):
        n = _parse_count_token(m.group("n"))
        if n:
            total += n
            found = True
    return total if found else None


def _extract_device_inventory(text: str) -> Optional[Dict[str, int]]:
    """
    Explicit router/switch/host inventory from free text.
    Complete when at least one host/PC count and at least one L2/L3 device
    count are stated. Returns None when the request is not a full flat inventory.
    """
    routers = _sum_device_role_counts(text, r"(?:routers?|gateways?)")
    # switch(?:es)? — not switches? — because the latter is "switche" + optional s.
    switches = _sum_device_role_counts(text, r"switch(?:es)?")
    hosts = _sum_device_role_counts(text, _HOST_DEVICE_WORDS)
    if hosts is None or hosts < 1:
        return None
    if routers is None and switches is None:
        return None
    return {
        "router_count": int(routers or 0),
        "switch_count": int(switches or 0),
        "host_count": int(hosts),
    }


def _has_organizational_language(text: str) -> bool:
    """True when the request implies departments / org VLAN groups."""
    if not text:
        return False
    if re.search(r"\bdepartments?\b", text, flags=re.IGNORECASE):
        return True
    if re.search(
        r"\b(?:vlan\s*groups?|org(?:anis|aniz)ational\s+units?)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return True
    if _requested_department_count(text) > 0:
        return True
    if _extract_department_names(text):
        return True
    if _named_departments_in_text(text):
        return True
    return False


def _is_flat_inventory_request(user_input: str, history: List[dict]) -> bool:
    """
    Explicit device-type counts, no org/department language, no delegation.
    Only then is the departments fatal-gap skipped.
    """
    if _is_user_delegation(user_input, history):
        return False
    text = _user_messages_text(user_input, history)
    if _has_organizational_language(text):
        return False
    return _extract_device_inventory(text) is not None


def _requested_literal_hosts_each(text: str) -> int:
    """
    Per-department host/PC device count from device phrasing (not 'N users').
    0 when absent or when only user-count phrasing is present.
    """
    if not text:
        return 0
    # User-count phrasing wins for sizing; it must not become host_nodes.
    if _requested_users_each(text):
        return 0
    patterns = (
        rf"\b{_COUNT_TOKEN}\s+{_HOST_DEVICE_WORDS}\s+each\b",
        rf"\b(?:with|and)\s+{_COUNT_TOKEN}\s+{_HOST_DEVICE_WORDS}\b",
        rf"\b{_COUNT_TOKEN}\s+{_HOST_DEVICE_WORDS}\b",
    )
    for pat in patterns:
        m = re.search(pat, text, flags=re.IGNORECASE)
        if not m:
            continue
        n = _parse_count_token(m.group("n"))
        if n:
            return n
    return 0


def _annotate_department_host_nodes(
    depts: List[Dict[str, Any]], user_text: str
) -> List[Dict[str, Any]]:
    """
    Attach host_nodes for small literal device counts. Large counts and
    'N users' phrasing keep the one-representative-host default.
    """
    n = _requested_literal_hosts_each(user_text)
    if not n or n > LITERAL_HOST_NODE_THRESHOLD:
        return depts
    out: List[Dict[str, Any]] = []
    for d in depts:
        row = dict(d)
        row["host_nodes"] = n
        out.append(row)
    return out


def _mentioned_in_user_text(name: str, user_text: str) -> bool:
    """Whether a department name appears in the user's own words."""
    if not name or not user_text:
        return False
    if name.strip().lower() in _NON_DEPARTMENT_WORDS:
        return False
    return re.search(rf"\b{re.escape(name.strip())}\b", user_text, flags=re.IGNORECASE) is not None


def _assign_vlan_ids(depts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Normalizes a department list to unique, in-range VLAN ids."""
    used: set = set()
    out: List[Dict[str, Any]] = []
    for i, d in enumerate(depts):
        try:
            vid = int(d.get("vlan_id"))
        except (TypeError, ValueError):
            vid = 0
        if vid < 2 or vid > 4094 or vid in used:
            vid = 10 * (i + 1)
            while vid in used or vid > 4094:
                vid += 10
        used.add(vid)
        try:
            users = int(d.get("users", 20))
        except (TypeError, ValueError):
            users = 20
        out.append({"name": d.get("name"), "users": users, "vlan_id": vid})
    return out


def _pad_to_requested_count(
    depts: List[Dict[str, Any]], requested: int, users_each: int
) -> List[Dict[str, Any]]:
    """Tops a department list up to a requested count using the SME ladder."""
    out = list(depts)
    taken = {str(d.get("name", "")).strip().lower() for d in out}
    default_users = users_each or (out[0].get("users", 20) if out else 20)
    for name in _SME_DEPARTMENT_LADDER:
        if len(out) >= requested:
            break
        if name.lower() in taken:
            continue
        taken.add(name.lower())
        out.append({"name": name, "users": default_users, "vlan_id": 0})
    i = 1
    while len(out) < requested:
        name = f"Dept{i}"
        if name.lower() not in taken:
            taken.add(name.lower())
            out.append({"name": name, "users": default_users, "vlan_id": 0})
        i += 1
    return _assign_vlan_ids(out)


def _infer_departments_from_free_text(text: str) -> List[str]:
    """
    Extract department names without requiring 'departments:' prefix.
    Handles e.g. 'two departments IT, CS, 2 sites', 'IT and CS', 'department IT, Finance'.
    """
    if not text:
        return []
    t = text.strip()
    candidates: List[str] = []

    # A hyphenated "4-department SME" is a size adjective, not a list introducer —
    # what follows it describes the organisation, not a department. The spaced
    # form ("4 departments IT, HR") is still handled as a list below.
    t = re.sub(
        r"\b(?:\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")-departments?\b",
        " ",
        t,
        flags=re.IGNORECASE,
    )

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

    # Recognised department words and bare acronyms, in the order written.
    if not candidates:
        candidates = _named_departments_in_text(t)

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


def _strip_trailing_list_qualifiers(raw: str) -> str:
    """
    Cut a trailing global qualifier off a department-list span before it is
    split on commas. Otherwise ", with 5 PCs each" is treated as another name.
    """
    if not raw:
        return raw
    qualifier_nouns = rf"(?:users?|{_HOST_DEVICE_WORDS}|employees?)"
    cut = re.split(
        rf"\s*(?:,\s*)?\b(?:with|having|using|including)\b\s+"
        rf"(?:{_COUNT_TOKEN}\s+)?{qualifier_nouns}\b",
        raw,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return cut.strip(" ,")


def _extract_department_names(text: str) -> List[str]:
    """
    Heuristic extraction of department names from free text.
    Supports patterns like:
    - departments: HR, IT, Finance
    - department HR, IT and Finance
    """
    if not text:
        return []
    # Same guard as the free-text inference: "4-department SME" introduces no list.
    text = re.sub(
        r"\b(?:\d{1,2}|" + "|".join(_NUMBER_WORDS) + r")-departments?\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    m = re.search(r"departments?\s*[:\-]?\s*([^\n\.]+)", text, flags=re.IGNORECASE)
    if not m:
        return []
    # Same idea as _infer_departments_from_free_text: stop the capture at a
    # trailing qualifier before splitting on comma/and.
    raw = _strip_trailing_list_qualifiers(m.group(1))
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


def _apply_sme_device_defaults(p: Dict[str, Any]) -> Dict[str, Any]:
    """Shared SME scope fields (models, OSPF, addressing)."""
    p["protocols"] = ["ospf"]
    p["ospf"] = {"area": 0}
    p["connectivity"] = p.get(
        "connectivity", "Internal campus connectivity with internet gateway"
    )
    p["security"] = p.get("security") or ["vlans"]
    p["devices"] = {
        "router": "Cisco 1941",
        "switch": "Catalyst 2960",
        "addressing": "IPv4 private",
    }
    p.pop("vpn", None)
    p.pop("firewall", None)
    p.pop("services", None)
    p.pop("external_services", None)
    return p


def _apply_sme_defaults(plan: Dict[str, Any], user_input: str, history: List[dict]) -> Dict[str, Any]:
    """
    Enforce SME campus defaults and keep scope to Cisco 1941 + 2960, IPv4, VLAN, OSPF area 0.

    Two plan modes:
    - flat_inventory: explicit device counts, no org language → no departments required
    - departmental: existing SME / VLAN-segmented shape
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

    # Complete flat device inventory → skip department grounding entirely.
    if _is_flat_inventory_request(user_input, history):
        inv = _extract_device_inventory(user_text) or {}
        p["mode"] = "flat_inventory"
        p["router_count"] = int(inv.get("router_count", 0))
        p["switch_count"] = int(inv.get("switch_count", 0))
        p["host_count"] = int(inv.get("host_count", 0))
        p["departments"] = []
        p["vlans"] = []
        p["users_per_site"] = p.get("users_per_site", max(1, p["host_count"]))
        p["security"] = []
        return _apply_sme_device_defaults(p)

    p["mode"] = "departmental"
    p.pop("router_count", None)
    p.pop("switch_count", None)
    p.pop("host_count", None)

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
            row = {"name": name, "users": users_i, "vlan_id": vlan_i}
            if d.get("host_nodes") is not None:
                try:
                    hn = int(d.get("host_nodes"))
                    if 1 <= hn <= LITERAL_HOST_NODE_THRESHOLD:
                        row["host_nodes"] = hn
                except (TypeError, ValueError):
                    pass
            normalized.append(row)
        p["departments"] = normalized
    else:
        p["departments"] = []

    # Ground the model's list in the user's own words rather than replacing it.
    # Names the user never wrote are hallucinations and get dropped; names they
    # did write are kept with the model's users/VLAN detail, and anything the
    # model missed is appended. A narrower deterministic match must not discard
    # a correct proposal.
    if _is_user_delegation(user_input, history) and p["departments"]:
        # The user handed the choice over, so incidental department-like words in
        # their description are not a list to ground against.
        pass
    elif explicit_depts:
        grounded = [
            {**d, "name": _canonical_department(str(d.get("name", "")))}
            for d in p["departments"]
            if _mentioned_in_user_text(str(d.get("name", "")), user_text)
        ]
        known = {str(d.get("name", "")).strip().lower() for d in grounded}
        users_each = _requested_users_each(user_text)
        for n in explicit_depts:
            if n.strip().lower() in known:
                continue
            known.add(n.strip().lower())
            grounded.append({"name": n, "users": users_each or 20, "vlan_id": 0})
        p["departments"] = _assign_vlan_ids(grounded)
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
                users_each = _requested_users_each(user_text)
                p["departments"] = [
                    {"name": n, "users": users_each or 20, "vlan_id": 10 * (i + 1)}
                    for i, n in enumerate(inferred)
                ]

    # "a 4-department SME" states a count without naming anything; honour the
    # count rather than dropping the intent. Never trims — naming beats counting.
    requested_n = _requested_department_count(user_text)
    if requested_n and len(p["departments"]) < requested_n:
        p["departments"] = _pad_to_requested_count(
            p["departments"], requested_n, _requested_users_each(user_text)
        )

    p["departments"] = _annotate_department_host_nodes(p["departments"], user_text)

    # VLAN catalog (always mirror departments)
    p["vlans"] = [{"id": int(d["vlan_id"]), "name": str(d["name"])} for d in p["departments"]]

    # Fixed SME defaults/scope
    p["users_per_site"] = p.get("users_per_site", 20)
    p["security"] = ["vlans"]
    return _apply_sme_device_defaults(p)


def _is_user_delegation(user_input: str, history: List[dict]) -> bool:
    """
    True when user explicitly delegates technical decisions to the system.
    Naming departments explicitly is not delegation of the department set.
    """
    # Only a structurally named list ("departments X, Y") overrides delegation.
    # A bare vocabulary hit such as "a logistics depot" is a description of the
    # business, not the user picking their department set.
    if _extract_department_names(_user_messages_text(user_input, history)):
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
        {"name": n, "users": 20, "vlan_id": 10 * (i + 1)}
        for i, n in enumerate(_SME_DEPARTMENT_LADDER[:3])
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
