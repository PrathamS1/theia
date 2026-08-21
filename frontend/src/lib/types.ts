/* Shapes mirror the live Theia API responses (verified against :8000). */

export interface Health {
  status: 'healthy' | 'degraded';
  hydradb_connected: boolean;
  vector_store_loaded: boolean;
  /* Graph label counts are null until the server's background refresh has
   * measured them: on a 25k-document graph an unanchored `count(*)` can exceed
   * HydraDB's 30s statement timeout, so /api/health never blocks on them. */
  total_documents: number | null;
  total_persons: number | null;
  total_orgs: number | null;
  total_topics: number | null;
  total_facts: number | null;
  /* Vector count is read from the loaded index, so it is always a number. */
  total_vectors: number;
  /* Age of the label counts in seconds; null before the first refresh lands. */
  counts_age_seconds: number | null;
  /* NOTE: same_as_edges / supersedes_edges are hardcoded server-side and do
   * not reflect the real graph. Shown as "documented", never as live counts. */
  same_as_edges: number;
  supersedes_edges: number;
}

/* 'Metric' holds config/metric keys a document references. They used to be minted
 * as tautological Facts (`X metric_name is X`); modelling them as entities is what
 * removed 96% of the graph's noise. */
export type NodeLabel =
  | 'Document' | 'Person' | 'Org' | 'Ticket' | 'Project' | 'Fact' | 'Metric' | 'Topic';
export type EdgeType = 'SAME_AS' | 'SUPERSEDES' | 'MENTIONS' | 'HAS_FACT';

export interface GraphNode {
  data: {
    id: string;
    label: NodeLabel;
    name: string;
    source?: string;
    doc_id?: string;
    created_at?: string;
    /* Fact only. Present (true/false) once supersession status is known for
     * this node; absent means unknown, which the canvas treats as active. */
    is_active?: boolean;
    subject?: string;
  };
}

export interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
    type: EdgeType;
    label: string;
    confidence?: number;
    reason?: string;
  };
}

export interface Topology {
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
  /* Present only on a search response. `matched_documents` counts matches across
   * the WHOLE corpus, of which the seed shows the first `doc_limit` — without it
   * the toolbar could only report the subgraph size, which reads as if the
   * corpus contained just those few documents. */
  query?: string;
  matched_documents?: number;
}

/* Same shape as Topology -- returned by /api/graph/expand, the 1-hop
 * neighbourhood grafted onto the canvas when a node is expanded. */
export type ExpandResult = Topology;

export interface NodeDetail {
  id: string;
  label: string;
  name: string;
  source?: string;
  doc_id?: string;
  created_at?: string;
  full_body?: string;
  properties: Record<string, string | number>;
  /* Facts the document asserts — the most informative thing about it, and absent
   * from the card until now. */
  facts?: { id?: number; subject: string; attribute: string; value: string; created_at?: string }[];
  /* `name` was missing from this payload, so the panel could only render the type
   * ("MENTIONS Person") instead of who was actually mentioned. */
  connected_neighbors: { id: string; label: string; name?: string; relationship: string }[];
}

export interface Question {
  question_id: string;
  question_type: string;
  source_types?: string[];
  question: string;
  expected_doc_ids?: string[];
  gold_answer?: string;
  answer_facts?: string[];
}

export interface QuestionPage {
  total: number;
  offset: number;
  limit: number;
  categories: string[];
  questions: Question[];
}

export interface QueryResult {
  question: string;
  question_id: string | null;
  category: string;
  answer: string;
  citations: string[];
  abstained: boolean;
  latency_ms: number;
  gold_answer: string | null;
  expected_doc_ids: string[];
  answer_facts: string[];
  trace: {
    vector_anchors: { doc_id: string; score: number; title: string }[];
    traversed_entities: string[];
    active_facts: { subject: string; status: string; text: string }[];
    abstained: boolean;
    /* HydraDB bookmark pinning the exact graph epoch this answer was read from,
     * plus the Cypher that produced it. Null if the graph was unreachable. */
    snapshot?: {
      bookmark: string;
      read_epoch: number | null;
      cypher: string;
    } | null;
  };
}

export interface EvalCategory {
  count: number;
  doc_recall: number;
  invalid_extra_docs: number;
  correctness: number;
  completeness: number;
  composite_score: number;
}

export interface EvalLatest {
  summary: {
    total_questions: number;
    overall_composite_score: number;
    overall_correctness: number;
    overall_completeness: number;
    overall_doc_recall: number;
    overall_invalid_extra_docs: number;
    by_category: Record<string, EvalCategory>;
    correct_count?: number;
    correct_ratio?: string;
  };
  total_records: number;
}

export interface IntegrationStatusItem {
  toolkit: 'slack' | 'github' | string;
  status: 'ACTIVE' | 'INITIATED' | 'DISCONNECTED' | string;
  connected_account_id?: string | null;
  account_name?: string | null;
}

export interface IntegrationsStatusResponse {
  user_id: string;
  configured: boolean;
  error?: string;
  integrations: IntegrationStatusItem[];
}

export interface ConnectResponse {
  user_id: string;
  toolkit: string;
  connection_id?: string;
  auth_url?: string;
  status: string;
}

export interface SyncResponse {
  status: string;
  user_id?: string;
  source?: string;
  documents_synced?: number;
  chunks_vectorized?: number;
  facts_extracted?: number;
  resolution?: {
    same_as_edges: number;
    supersedes_edges: number;
  };
  results?: Record<string, any>;
  message?: string;
  error?: string;
}

export interface GitHubRepo {
  id: number;
  name: string;
  full_name: string;
  description?: string;
  private?: boolean;
  html_url?: string;
  stars?: number;
  updated_at?: string;
}

export interface GitHubReposResponse {
  user_id: string;
  total_repositories: number;
  repositories: GitHubRepo[];
}
