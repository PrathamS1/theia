import type {
  EvalLatest, ExpandResult, Health, NodeDetail, NodeLabel, QueryResult, QuestionPage, Topology,
  IntegrationsStatusResponse, ConnectResponse, SyncResponse, GitHubReposResponse,
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
    throw new ApiError('Cannot reach the API at /api - check that both the Vite dev server and uvicorn (:8000) are running.');
  }
  if (!res.ok) throw new ApiError(`Request failed (${res.status}) for ${path}`, res.status);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: any, signal?: AbortSignal): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal,
    });
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    throw new ApiError('Cannot reach the API at /api - check that both the Vite dev server and uvicorn (:8000) are running.');
  }
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new ApiError(detail?.detail ?? `Request failed (${res.status}) for ${path}`, res.status);
  }
  return res.json() as Promise<T>;
}

export const getHealth = (signal?: AbortSignal) => get<Health>('/api/health', signal);

/* doc_limit controls how many seed documents (and their MENTIONS/HAS_FACT
 * neighbours) are fetched -- the full graph is ~8k nodes / ~7.3k edges, far
 * past what Cytoscape renders usefully, so the canvas starts from this
 * bounded seed and grows via expandNode() as the user clicks. */
export function getTopology(
  opts: { docLimit?: number; labels?: string[]; search?: string; workspaceId?: string | null } = {},
  signal?: AbortSignal,
) {
  const p = new URLSearchParams();
  p.set('doc_limit', String(opts.docLimit ?? 30));
  if (opts.labels?.length) p.set('labels', opts.labels.join(','));
  if (opts.search?.trim()) p.set('search', opts.search.trim());
  if (opts.workspaceId) p.set('workspace_id', opts.workspaceId);
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
  workspaceId?: string | null,
  signal?: AbortSignal,
): Promise<QueryResult> {
  return post<QueryResult>(
    '/api/query',
    { question, question_id: questionId ?? null, workspace_id: workspaceId ?? null },
    signal,
  );
}

// ── Integrations APIs ────────────────────────────────────────────────────────

export const getIntegrationsStatus = (userId: string, signal?: AbortSignal) =>
  get<IntegrationsStatusResponse>(`/api/integrations/status?user_id=${encodeURIComponent(userId)}`, signal);

export const connectSlack = (userId: string, signal?: AbortSignal) =>
  post<ConnectResponse>('/api/integrations/connect/slack', { user_id: userId }, signal);

export const connectGitHub = (userId: string, signal?: AbortSignal) =>
  post<ConnectResponse>('/api/integrations/connect/github', { user_id: userId }, signal);

export const getGitHubRepos = (userId: string, signal?: AbortSignal) =>
  get<GitHubReposResponse>(`/api/integrations/github/repos?user_id=${encodeURIComponent(userId)}`, signal);

export const syncSlack = (userId: string, opts?: { maxChannels?: number; messagesPerChannel?: number }, signal?: AbortSignal) =>
  post<SyncResponse>('/api/integrations/sync/slack', {
    user_id: userId,
    max_channels: opts?.maxChannels ?? 5,
    messages_per_channel: opts?.messagesPerChannel ?? 30,
  }, signal);

export const syncGitHub = (userId: string, opts?: { selectedRepos?: string[]; maxRepos?: number; prsPerRepo?: number; issuesPerRepo?: number }, signal?: AbortSignal) =>
  post<SyncResponse>('/api/integrations/sync/github', {
    user_id: userId,
    selected_repos: opts?.selectedRepos,
    max_repos: opts?.maxRepos ?? 10,
    prs_per_repo: opts?.prsPerRepo ?? 20,
    issues_per_repo: opts?.issuesPerRepo ?? 20,
  }, signal);

export const syncAll = (userId: string, opts?: { selectedRepos?: string[] }, signal?: AbortSignal) =>
  post<SyncResponse>('/api/integrations/sync/all', {
    user_id: userId,
    selected_repos: opts?.selectedRepos,
  }, signal);
