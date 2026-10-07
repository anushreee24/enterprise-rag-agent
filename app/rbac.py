"""Role-based access control: the heart of the 'secure' in secure RAG.

Two independent attributes decide whether a role may see a chunk:
  1. classification level  (public < internal < confidential < restricted)
  2. department            (hr, finance, legal, ...)

The SAME policy is expressed twice:
  - chroma_filter(): pushed into the vector DB so unauthorised chunks are never
    even retrieved (pre-filtering -> no top-k starvation, no leakage)
  - can_access(): re-checked in Python on every returned chunk (defence in depth)
"""
from dataclasses import dataclass

CLASSIFICATION = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
DEPARTMENTS = ["general", "hr", "finance", "legal", "compliance", "it_security"]


@dataclass(frozen=True)
class Role:
    name: str
    clearance: int                       # max classification level readable
    departments: frozenset[str] | None   # None = every department
    can_ingest: bool = False
    can_view_audit: bool = False


ROLES: dict[str, Role] = {
    "employee": Role("employee", CLASSIFICATION["internal"], frozenset({"general"})),
    "hr_manager": Role("hr_manager", CLASSIFICATION["confidential"], frozenset({"general", "hr"})),
    "finance_analyst": Role("finance_analyst", CLASSIFICATION["confidential"], frozenset({"general", "finance"})),
    "compliance_officer": Role(
        "compliance_officer", CLASSIFICATION["restricted"],
        frozenset({"general", "compliance", "legal", "it_security"}), can_view_audit=True),
    "admin": Role("admin", CLASSIFICATION["restricted"], None, can_ingest=True, can_view_audit=True),
}


def get_role(name: str) -> Role:
    if name not in ROLES:
        raise KeyError(f"Unknown role: {name}")
    return ROLES[name]


def can_access(role: Role, meta: dict) -> bool:
    """Python-side policy check on one chunk's metadata. Fails closed."""
    level = meta.get("classification_level")
    dept = meta.get("department")
    if level is None or dept is None:
        return False
    if level > role.clearance:
        return False
    return role.departments is None or dept in role.departments


def chroma_filter(role: Role) -> dict:
    """Same policy as a ChromaDB `where` clause."""
    level = {"classification_level": {"$lte": role.clearance}}
    if role.departments is None:
        return level
    return {"$and": [level, {"department": {"$in": sorted(role.departments)}}]}
