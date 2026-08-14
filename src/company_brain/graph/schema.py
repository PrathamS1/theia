"""
graph/schema.py — all node labels, edge types, and property name constants.

No logic here. Import from this module everywhere labels/properties are needed
so that a single rename propagates across the codebase.
"""


# ── Node labels ───────────────────────────────────────────────────────────────
class NodeLabel:
    PERSON = "Person"
    ORG = "Org"
    PROJECT = "Project"
    DEAL = "Deal"
    TICKET = "Ticket"
    DOCUMENT = "Document"
    FACT = "Fact"


# ── Edge (relationship) types ─────────────────────────────────────────────────
class EdgeType:
    # Raw extraction
    MENTIONS = "MENTIONS"
    # Entity resolution
    SAME_AS = "SAME_AS"
    # Structural / participation
    ASSIGNED_TO = "ASSIGNED_TO"
    DISCUSSED_IN = "DISCUSSED_IN"
    OWNED_BY = "OWNED_BY"
    WORKS_AT = "WORKS_AT"
    PART_OF = "PART_OF"
    # Conflict resolution
    SUPERSEDES = "SUPERSEDES"


# ── Property names — nodes ────────────────────────────────────────────────────
class NodeProp:
    # Shared
    ID = "id"
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

    # Person
    CANONICAL_NAME = "canonical_name"
    EMAILS = "emails"           # list[str]
    HANDLES = "handles"         # list[str]  (Slack handles, GitHub logins, etc.)
    RESOLVED_FROM = "resolved_from"  # list[str] — original mention strings

    # Org
    DOMAIN = "domain"

    # Project / Ticket
    STATUS = "status"
    SOURCE_SYSTEM = "source_system"
    TITLE = "title"

    # Deal
    STAGE = "stage"
    AMOUNT = "amount"

    # Document
    SOURCE = "source"       # e.g. "slack", "gmail", "linear"
    DOC_ID = "doc_id"
    URL = "url"
    RAW_TEXT_REF = "raw_text_ref"  # path or key to raw text if needed

    # Fact
    SUBJECT = "subject"
    ATTRIBUTE = "attribute"
    VALUE = "value"
    TRUST_SCORE = "trust_score"   # float 0..1, derived from source


# ── Property names — edges ────────────────────────────────────────────────────
class EdgeProp:
    # Provenance — on EVERY fact-bearing edge
    SOURCE = "source"           # e.g. "slack", "gmail"
    TIMESTAMP = "timestamp"     # ISO-8601 string
    CONFIDENCE = "confidence"   # float 0..1
    DOC_ID = "doc_id"           # back-reference to Document.doc_id

    # SAME_AS
    EVIDENCE = "evidence"       # list[str] — doc_ids that justify the merge

    # SUPERSEDES
    REASON = "reason"           # brief free-text explanation


# ── Source trust ranking (higher = more authoritative) ───────────────────────
# Used as a tie-breaker when two facts have the same timestamp.
SOURCE_TRUST: dict[str, float] = {
    "linear": 0.95,        # structured, intentional project records
    "github": 0.92,        # code/PR records are rarely wrong
    "confluence": 0.90,    # official wiki content
    "hubspot": 0.88,       # CRM system of record for deals
    "fireflies": 0.75,     # meeting transcripts — spoken word, may be noisy
    "slack": 0.65,         # conversational, opinions and drafts mixed in
    "drive": 0.70,         # docs vary wildly in authority
    "gmail": 0.60,         # emails include speculation and outdated threads
}

DEFAULT_TRUST: float = 0.50  # for unknown/unclassified sources


def trust_for(source: str) -> float:
    return SOURCE_TRUST.get(source.lower(), DEFAULT_TRUST)
