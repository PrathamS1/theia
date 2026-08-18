import type {
  EvalLatest, ExpandResult, Health, NodeDetail, NodeLabel, QueryResult, QuestionPage, Topology,
} from './types';

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, { signal });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    throw new ApiError('Cannot reach the Theia API. Is uvicorn running on :8000?');
  }
  if (!res.ok) throw new ApiError(`Request failed (${res.status}) for ${path}`, res.status);
  return res.json() as Promise<T>;
}

export const getHealth = (signal?: AbortSignal) => get<Health>('/api/health', signal);

/* doc_limit controls how many seed documents (and their MENTIONS/HAS_FACT
 * neighbours) are fetched -- the full graph is ~8k nodes / ~7.3k edges, far
 * past what Cytoscape renders usefully, so the canvas starts from this
 * bounded seed and grows via expandNode() as the user clicks. */
export function getTopology(
  opts: { docLimit?: number; labels?: string[]; search?: string } = {},
  signal?: AbortSignal,
) {
  const p = new URLSearchParams();
  p.set('doc_limit', String(opts.docLimit ?? 30));
  if (opts.labels?.length) p.set('labels', opts.labels.join(','));
  if (opts.search?.trim()) p.set('search', opts.search.trim());
  return get<Topology>(`/api/graph/topology?${p}`, signal);
}

/* 1-hop neighbourhood of a single node (anchored Cypher lookup, ~10-75ms) to
 * graft onto the existing canvas without a full topology refetch. */
export const expandNode = (nodeId: string, label: NodeLabel, signal?: AbortSignal) =>
  get<ExpandResult>(
    `/api/graph/expand?node_id=${encodeURIComponent(nodeId)}&label=${encodeURIComponent(label)}`,
    signal,
  );

export const getNodeDetail = (id: string, signal?: AbortSignal) =>
  get<NodeDetail>(`/api/graph/node/${encodeURIComponent(id)}`, signal);

export function getQuestions(
  opts: { category?: string; search?: string; limit?: number; offset?: number } = {},
  signal?: AbortSignal,
) {
  const p = new URLSearchParams();
  if (opts.category && opts.category !== 'all') p.set('category', opts.category);
  if (opts.search?.trim()) p.set('search', opts.search.trim());
  p.set('limit', String(opts.limit ?? 50));
  p.set('offset', String(opts.offset ?? 0));
  return get<QuestionPage>(`/api/questions?${p}`, signal);
}

export const getEvalLatest = (signal?: AbortSignal) =>
  get<EvalLatest>('/api/eval/latest', signal);

export async function runQuery(
  question: string,
  questionId?: string | null,
  signal?: AbortSignal,
): Promise<QueryResult> {
  let res: Response;
  try {
    res = await fetch('/api/query', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, question_id: questionId ?? null }),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    throw new ApiError('Cannot reach the Theia API. Is uvicorn running on :8000?');
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new ApiError(detail?.detail ?? `Query failed (${res.status})`, res.status);
  }
  return res.json();
}
