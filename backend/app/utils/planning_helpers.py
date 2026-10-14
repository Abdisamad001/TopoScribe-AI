from app.utils.dept_labels import (
    filter_department_string_list,
    is_plausible_department_name,
    sanitize_department_name,
)
from typing import Dict, Any, List, Optional
import re

LITERAL_HOST_NODE_THRESHOLD = 8

# Department words
_DEPARTMENT_VOCABULARY = (
    "accounting", "administration", "admin", "customer service",
    "engineering", "facilities", "finance", "human resources", "hr", "it",
    "legal", "logistics", "maintenance", "manufacturing", "marketing",
    "operations", "ops", "procurement", "production", "purchasing",
    "quality assurance", "qa", "research", "sales", "security", "support",
    "training", "warehouse",
)

# Words that describe the request 
_NON_DEPARTMENT_WORDS = {
    "design", "network", "networks", "topology", "site", "sites", "office",
    "offices", "campus", "company", "business", "branch", "user", "users",
    "pc", "pcs", "device", "devices", "department", "departments",
}

_DEPARTMENT_ACRONYMS = {"hr", "it", "qa", "ops"}

# Uppercase tokens 
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

#Consistent display casing, acronyms like 'JS' to 'Js'
def _canonical_department(word: str) -> str:
    
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

#Digits, number-words
def _parse_count_token(token: str) -> int:
   
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
    if _is_user_delegation(user_input, history):
        return False
    text = _user_messages_text(user_input, history)
    if _has_organizational_language(text):
        return False
    return _extract_device_inventory(text) is not None


def _requested_literal_hosts_each(text: str) -> int:
    if not text:
        return 0
   
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
    n = _requested_literal_hosts_each(user_text)
    if not n or n > LITERAL_HOST_NODE_THRESHOLD:
        return depts
    out: List[Dict[str, Any]] = []
    for d in depts:
        row = dict(d)
        row["host_nodes"] = n
        out.append(row)
    return out

# Dept mentioned in user text
def _mentioned_in_user_text(name: str, user_text: str) -> bool:
 
    if not name or not user_text:
        return False
    if name.strip().lower() in _NON_DEPARTMENT_WORDS:
        return False
    return re.search(rf"\b{re.escape(name.strip())}\b", user_text, flags=re.IGNORECASE) is not None


def _assign_vlan_ids(depts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:

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
    if not text:
        return []
    t = text.strip()
    candidates: List[str] = []

  
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

    parts = [user_input or ""]
    for m in history or []:
        if (m or {}).get("role") == "user":
            parts.append(str((m or {}).get("content", "")))
    return " ".join(p for p in parts if p).strip()


def _explicit_departments_from_user(user_input: str, history: List[dict]) -> List[str]:
  
    text = _user_messages_text(user_input, history)
    inferred = _extract_department_names(text)
    if not inferred:
        inferred = _infer_departments_from_free_text(text)
    return inferred


def _strip_trailing_list_qualifiers(raw: str) -> str:
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
    if not text:
        return []
   
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
    p = dict(plan or {})
    user_text = _user_messages_text(user_input, history)
    explicit_depts = _explicit_departments_from_user(user_input, history)

    
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

  
    if _is_user_delegation(user_input, history) and p["departments"]:
       
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

    # "a 4-department SME" states a count without naming anything; 
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
