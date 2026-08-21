import { useCallback, useRef, useState } from 'react';
import { FileText, User, Building2, Ticket as TicketIcon, FolderGit2, Sparkles, Gauge, Settings2, Globe, Zap, Trash2, Hash, Search, Loader2, X } from 'lucide-react';
import { getEvalLatest, getHealth, getTopology } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import { useDebouncedValue } from '../lib/useDebouncedValue';
import type { NodeLabel } from '../lib/types';
import StatusBar from '../components/StatusBar';
import GraphCanvas, { type GraphCanvasHandle, type LayoutName } from '../components/GraphCanvas';
import GraphLegend from '../components/GraphLegend';
import NodeInspector from '../components/NodeInspector';
import AskPanel from '../components/AskPanel';
import QuestionPicker from '../components/QuestionPicker';
import LiveIntegrationsModal from '../components/LiveIntegrationsModal';
import './Dashboard.css';

const ALL_LABELS: NodeLabel[] =
  ['Document', 'Person', 'Org', 'Ticket', 'Project', 'Fact', 'Metric', 'Topic'];

/* An icon per node type. The chips were seven near-identical text pills; a glyph
 * makes each scannable without reading, and matches the swatch colour used on the
 * canvas so the filter and the graph speak the same language. */
const LABEL_ICON: Record<NodeLabel, typeof FileText> = {
  Document: FileText,
  Person: User,
  Org: Building2,
  Ticket: TicketIcon,
  Project: FolderGit2,
  Fact: Sparkles,
  Metric: Gauge,
  Topic: Hash,
};
const DEFAULT_DOC_LIMIT = 30;
/* Named for what they SHOW, not for their algorithm. `breadthfirst` ("Tree") was
 * removed: most documents sit at the same depth in this topology, so it drew 108
 * nodes as flat rows and implied a hierarchy that does not exist. */
const LAYOUTS: { id: LayoutName; name: string; hint: string }[] = [
  { id: 'cose', name: 'Clusters', hint: 'Force-directed — groups what is densely connected' },
  { id: 'concentric', name: 'By links', hint: 'Most-connected nodes in the centre' },
  { id: 'grid', name: 'Grid', hint: 'Even spacing, no structure implied' },
];

export default function Dashboard() {
  // Multi-tenant user workspace identity (dynamic, persisted in localStorage)
  const [userName, setUserName] = useState(() => localStorage.getItem('theia_user_name') || '');
  const [userId, setUserId] = useState(() => localStorage.getItem('theia_user_id') || '');
  const [workspaceMode, setWorkspaceMode] = useState<'benchmark' | 'live'>('benchmark');
  const [isIntegrationsOpen, setIsIntegrationsOpen] = useState(false);

  const [labels, setLabels] = useState<NodeLabel[]>(ALL_LABELS);
  /* `draft` is what is typed; `search` is what has been applied. These used to
   * be joined only by a form submit, so typing did nothing until you pressed
   * Enter — the field looked broken. It now applies itself once typing pauses,
   * and `pending` drives an inline spinner so the pause reads as work. */
  const [draft, setDraft] = useState('');
  const search = useDebouncedValue(draft, 350);
  const searchPending = draft !== search;
  // Force-directed by default. `breadthfirst` ("Tree") lays this topology out as a
  // single flat row -- most documents sit at the same depth, so the hierarchy it
  // draws is meaningless and the graph reads as a line of dots across an otherwise
  // empty canvas. Force layout shows the actual clustering.
  const [layout, setLayout] = useState<LayoutName>('cose');
  const [selected, setSelected] = useState<string | null>(null);
  const [preset, setPreset] = useState<{ q: string; id: string } | null>(null);
  const canvasRef = useRef<GraphCanvasHandle>(null);

  const activeWorkspaceId = workspaceMode === 'live' ? userId : null;

  const health = useAsync((s) => getHealth(s), []);
  const evalLatest = useAsync((s) => getEvalLatest(s), []);

  const topo = useAsync(
    (s) => getTopology({ docLimit: DEFAULT_DOC_LIMIT, labels, search, workspaceId: activeWorkspaceId }, s),
    [labels.join(','), search, activeWorkspaceId],
  );

  const handleUserChange = (name: string, id: string) => {
    setUserName(name);
    setUserId(id);
    localStorage.setItem('theia_user_name', name);
    localStorage.setItem('theia_user_id', id);
  };

  const toggleLabel = (l: NodeLabel) =>
    setLabels((cur) => (cur.includes(l) ? cur.filter((x) => x !== l) : [...cur, l]));

  const focusCitations = useCallback((docIds: string[]) => {
    if (docIds.length) setSelected(`doc_${docIds[0]}`);
  }, []);

  const handleExpand = useCallback(async (nodeId: string, label: NodeLabel) => {
    await canvasRef.current?.expandNode(nodeId, label);
  }, []);

  return (
    <div className="dash">
      <a className="skip-link" href="#canvas">Skip to graph</a>
      <StatusBar health={health.data} healthError={health.error} evalData={evalLatest.data} />

      {/* Primary Top Bar: Workspace Selector & Integrations Trigger */}
      <div className="dash-workspace-bar">
        <div className="workspace-toggle-group">
          <button
            className={`btn btn-sm ${workspaceMode === 'benchmark' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => setWorkspaceMode('benchmark')}
          >
            <Globe size={14} aria-hidden="true" /> Enterprise Benchmark Corpus
          </button>
          <button
            className={`btn btn-sm ${workspaceMode === 'live' ? 'btn-primary' : 'btn-outline'}`}
            onClick={() => {
              if (!userId) {
                setIsIntegrationsOpen(true);
              } else {
                setWorkspaceMode('live');
              }
            }}
          >
            <Zap size={14} aria-hidden="true" />
            {userName ? `${userName}’s Live Workspace` : 'Live Mode (Connect SaaS)'}
          </button>

          {workspaceMode === 'live' && userId && (
            <button
              className="btn btn-sm btn-danger-outline"
              title="Delete all ingested graph nodes, vectors, and documents for this workspace"
              onClick={async () => {
                const ok = window.confirm(
                  `Are you sure you want to purge all live data for workspace '${userId}'?\n\nThis will completely delete all your ingested Slack and GitHub graph nodes, vector embeddings, and staged files from HydraDB so you can re-create them cleanly.`
                );
                if (ok) {
                  try {
                    const { purgeWorkspace } = await import('../lib/api');
                    await purgeWorkspace(userId);
                    setSelected(null);
                    topo.reload();
                    alert(`Successfully purged workspace '${userId}'! You can now ingest fresh data.`);
                  } catch (err: any) {
                    alert(`Failed to purge workspace: ${err.message || err}`);
                  }
                }
              }}
            >
              <Trash2 size={14} aria-hidden="true" /> Purge Workspace
            </button>
          )}
        </div>

        <button
          className="btn btn-sm btn-accent"
          onClick={() => setIsIntegrationsOpen(true)}
        >
          <Settings2 size={14} aria-hidden="true" /> Manage Integrations
        </button>
      </div>

      <div className="dash-toolbar">
        <fieldset className="filter-set">
          <legend className="sr-only">Filter node types</legend>
          {ALL_LABELS.map((l) => {
            const Icon = LABEL_ICON[l];
            return (
              <label key={l} className={`chip ${labels.includes(l) ? 'chip-on' : ''}`}>
                <input
                  type="checkbox" className="sr-only"
                  checked={labels.includes(l)} onChange={() => toggleLabel(l)}
                />
                <Icon size={13} aria-hidden="true" />
                {l}
              </label>
            );
          })}
        </fieldset>

        <div className="tb-search">
          <label className="sr-only" htmlFor="graph-search">Filter documents by title</label>
          <Search size={14} className="tbs-icon" aria-hidden="true" />
          <input
            id="graph-search" type="text" className="field field-sm tbs-input"
            placeholder="Filter documents…" value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Escape') setDraft(''); }}
          />
          {/* Occupies one slot so the field's width never jumps between the
            * three states. */}
          <span className="tbs-trail">
            {searchPending
              ? <Loader2 size={13} className="spin" aria-label="Filtering" />
              : draft
                ? (
                  <button type="button" className="tbs-clear" onClick={() => setDraft('')} aria-label="Clear filter">
                    <X size={13} aria-hidden="true" />
                  </button>
                )
                : null}
          </span>
        </div>

        <div className="tb-layout" role="group" aria-label="Graph layout">
          {LAYOUTS.map((l) => (
            <button
              key={l.id}
              className={`btn btn-sm ${layout === l.id ? 'btn-on' : ''}`}
              onClick={() => setLayout(l.id)}
              aria-pressed={layout === l.id}
              title={l.hint}
            >
              {l.name}
            </button>
          ))}
        </div>

        <span className="tb-count" title="Double-click a node, or use Expand in the inspector, to grow the graph">
          {!topo.data
            ? '—'
            : topo.data.matched_documents !== undefined
              ? `${topo.data.matched_documents.toLocaleString()} document${topo.data.matched_documents === 1 ? '' : 's'} match · showing ${topo.data.total_nodes.toLocaleString()} nodes`
              : `${topo.data.total_nodes.toLocaleString()} node${topo.data.total_nodes === 1 ? '' : 's'} · ${topo.data.total_edges.toLocaleString()} edge${topo.data.total_edges === 1 ? '' : 's'} (seed)`}
        </span>
      </div>

      <main id="canvas" className="dash-canvas">
        {topo.loading && (
          <div className="canvas-state" aria-busy="true">
            <span className="skeleton canvas-sk" />
            <p className="muted small">Loading graph…</p>
          </div>
        )}

        {topo.error && (
          <div className="canvas-state" role="alert">
            <h3>Could not load the graph</h3>
            <p className="muted small">{topo.error}</p>
            <button className="btn" onClick={topo.reload}>Retry</button>
          </div>
        )}

        {!topo.loading && !topo.error && topo.data && topo.data.nodes.length === 0 && (
          <div className="canvas-state" role="status">
            <h3>No nodes in this view</h3>
            <p className="muted small">
              {workspaceMode === 'live'
                ? `No live documents found for workspace '${userId}'. Connect your Slack or GitHub account above to sync real data.`
                : 'Clear the search or re-enable a node type.'}
            </p>
            {workspaceMode === 'live' ? (
              <button className="btn btn-primary" onClick={() => setIsIntegrationsOpen(true)}>
                Connect & Sync Apps
              </button>
            ) : (
              <button className="btn" onClick={() => { setDraft(''); setLabels(ALL_LABELS); }}>
                Reset filters
              </button>
            )}
          </div>
        )}

        {/* People connect to each other THROUGH documents, so hiding Document
          * legitimately removes every MENTIONS edge and leaves only the 78 direct
          * SAME_AS identity bridges. Without this note that reads as a broken
          * graph rather than as what the ontology actually says. */}
        {!topo.loading && !topo.error && topo.data && topo.data.nodes.length > 0 &&
          topo.data.total_edges <= 1 && topo.data.total_nodes > 5 && !labels.includes('Document') && (
          <div className="canvas-note" role="status">
            <span>
              <strong>{topo.data.total_nodes} nodes, {topo.data.total_edges} link
              {topo.data.total_edges === 1 ? '' : 's'}.</strong>{' '}
              These connect to each other <em>through documents</em> — hiding Document hides those links.
            </span>
            <button
              className="btn btn-sm btn-primary"
              onClick={() => setLabels((cur) => [...cur, 'Document'])}
            >
              Show connections
            </button>
          </div>
        )}

        {!topo.loading && !topo.error && topo.data && topo.data.nodes.length > 0 && (
          <GraphCanvas
            ref={canvasRef}
            topology={topo.data} layout={layout}
            selectedId={selected} workspaceId={activeWorkspaceId} onSelect={setSelected}
          />
        )}

        <GraphLegend />

        {selected && (
          <NodeInspector nodeId={selected} workspaceId={activeWorkspaceId} onClose={() => setSelected(null)} onExpand={handleExpand} />
        )}
      </main>

      <aside className="dash-side">
        <AskPanel
          presetQuestion={preset?.q ?? ''}
          presetId={preset?.id ?? null}
          workspaceId={activeWorkspaceId}
          onClearPreset={() => setPreset(null)}
          onCitations={focusCitations}
        />
        <div className="side-divider" />
        <QuestionPicker
          activeId={preset?.id ?? null}
          onPick={(q, id) => setPreset({ q, id })}
        />
      </aside>

      {/* Live Integrations Modal */}
      <LiveIntegrationsModal
        isOpen={isIntegrationsOpen}
        onClose={() => setIsIntegrationsOpen(false)}
        userName={userName}
        userId={userId}
        onUserChange={handleUserChange}
        onSyncComplete={() => {
          topo.reload();
          setWorkspaceMode('live');
        }}
      />
    </div>
  );
}
