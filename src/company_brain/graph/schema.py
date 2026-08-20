"""
graph/schema.py — all node labels, edge types, and property name constants.
Updated for graph-native rebuild: adds Topic (for facts not about a named entity)
and ABOUT (structural link from Fact to Entity or Topic).
"""


class NodeLabel:
    PERSON = "Person"
    ORG = "Org"
    PROJECT = "Project"
    DEAL = "Deal"
    TICKET = "Ticket"
    DOCUMENT = "Document"
    FACT = "Fact"
    TOPIC = "Topic"          # Subject anchor for facts not about a named entity
    ENTITY = "Entity"        # Fallback label for untyped extracted entities


class EdgeType:
    # Raw extraction
    MENTIONS = "MENTIONS"          # (Document)->(Entity), carries provenance properties
    SAME_AS = "SAME_AS"            # (Person)->(Person), resolved identity
    ASSIGNED_TO = "ASSIGNED_TO"
    DISCUSSED_IN = "DISCUSSED_IN"
    OWNED_BY = "OWNED_BY"
    WORKS_AT = "WORKS_AT"
    PART_OF = "PART_OF"
    HAS_FACT = "HAS_FACT"          # (Document)->(Fact)
    ABOUT = "ABOUT"                # (Fact)->(Entity|Topic), the structural link
    SUPERSEDES = "SUPERSEDES"      # (Fact)->(Fact)


class NodeProp:
    # Shared
    ID = "id"
    NAME = "name"
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"

    # Person
    CANONICAL_NAME = "canonical_name"
    EMAILS = "emails"           # list[str]
    HANDLES = "handles"         # list[str]
    RESOLVED_FROM = "resolved_from"

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
    SOURCE = "source"              # fine-grained category (e.g. "terraform-and-iac")
    SOURCE_ROOT = "source_root"    # top-level folder (e.g. "confluence"), used for trust
    DOC_ID = "doc_id"
    URL = "url"
    RAW_TEXT_REF = "raw_text_ref"

    # Fact
    SUBJECT = "subject"
    ATTRIBUTE = "attribute"
    VALUE = "value"
    TRUST_SCORE = "trust_score"   # float 0..1, derived from source


class EdgeProp:
    # Provenance
    SOURCE = "source"           # e.g. "slack", "gmail"
    TIMESTAMP = "timestamp"     # ISO-8601 string
    CONFIDENCE = "confidence"   # float 0..1
    DOC_ID = "doc_id"           # back-reference to Document.doc_id
    EVIDENCE = "evidence"
    METHOD = "method"           # "structural" | "name_similarity" | "llm"
    REASON = "reason"


SOURCE_TRUST: dict[str, float] = {
    "linear": 0.95,
    "jira": 0.95,
    "github": 0.92,
    "confluence": 0.90,
    "hubspot": 0.88,
    "fireflies": 0.75,
    "slack": 0.65,
    "google_drive": 0.70,
    "drive": 0.70,
    "gmail": 0.60,
}
DEFAULT_TRUST: float = 0.50

KNOWN_ENTITY_LABELS = {"Person", "Org", "Project", "Ticket", "Deal"}


def trust_for(source_root: str) -> float:
    return SOURCE_TRUST.get((source_root or "").lower(), DEFAULT_TRUST)
