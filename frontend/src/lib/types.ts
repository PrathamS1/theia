/* Shapes mirror the live Theia API responses (verified against :8000). */

export interface Health {
  status: 'healthy' | 'degraded';
  hydradb_connected: boolean;
  vector_store_loaded: boolean;
  total_documents: number;
  total_persons: number;
  total_facts: number;
  total_vectors: number;
  /* NOTE: same_as_edges / supersedes_edges are hardcoded server-side and do
   * not reflect the real graph. Shown as "documented", never as live counts. */
  same_as_edges: number;
  supersedes_edges: number;
}

export type NodeLabel = 'Document' | 'Person' | 'Org' | 'Ticket' | 'Project' | 'Fact';
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
  connected_neighbors: { id: string; label: string; relationship: string }[];
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
