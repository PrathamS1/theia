import { useCallback, useRef, useState } from 'react';
import { getEvalLatest, getHealth, getTopology } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import type { NodeLabel } from '../lib/types';
import StatusBar from '../components/StatusBar';
import GraphCanvas, { type GraphCanvasHandle, type LayoutName } from '../components/GraphCanvas';
import GraphLegend from '../components/GraphLegend';
import NodeInspector from '../components/NodeInspector';
import AskPanel from '../components/AskPanel';
import QuestionPicker from '../components/QuestionPicker';
import './Dashboard.css';

const ALL_LABELS: NodeLabel[] = ['Document', 'Person', 'Org', 'Ticket', 'Project', 'Fact'];
const DEFAULT_DOC_LIMIT = 30;
const LAYOUTS: { id: LayoutName; name: string }[] = [
  { id: 'breadthfirst', name: 'Tree' },
  { id: 'concentric', name: 'Concentric' },
  { id: 'cose', name: 'Force' },
  { id: 'grid', name: 'Grid' },
];

export default function Dashboard() {
  const [labels, setLabels] = useState<NodeLabel[]>(ALL_LABELS);
  const [search, setSearch] = useState('');
  const [draft, setDraft] = useState('');
  const [layout, setLayout] = useState<LayoutName>('breadthfirst');
  const [selected, setSelected] = useState<string | null>(null);
  const [preset, setPreset] = useState<{ q: string; id: string } | null>(null);
  const canvasRef = useRef<GraphCanvasHandle>(null);

  const health = useAsync((s) => getHealth(s), []);
  const evalLatest = useAsync((s) => getEvalLatest(s), []);
  /* A bounded seed, not the full ~8k-node graph -- the user grows it from
   * here by clicking (or double-clicking) nodes on the canvas. */
  const topo = useAsync(
    (s) => getTopology({ docLimit: DEFAULT_DOC_LIMIT, labels, search }, s),
    [labels.join(','), search],
  );

  const toggleLabel = (l: NodeLabel) =>
    setLabels((cur) => (cur.includes(l) ? cur.filter((x) => x !== l) : [...cur, l]));

  /* Selecting the first citation surfaces the answer's evidence on the canvas
   * -- only takes effect if that document happens to be in the current seed
   * or has already been expanded into view; the seed is bounded by design. */
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

      <div className="dash-toolbar">
        <fieldset className="filter-set">
          <legend className="sr-only">Filter node types</legend>
          {ALL_LABELS.map((l) => (
            <label key={l} className={`chip ${labels.includes(l) ? 'chip-on' : ''}`}>
              <input
                type="checkbox" className="sr-only"
                checked={labels.includes(l)} onChange={() => toggleLabel(l)}
              />
              {l}
            </label>
          ))}
        </fieldset>

        <form className="tb-search" onSubmit={(e) => { e.preventDefault(); setSearch(draft); }}>
          <label className="sr-only" htmlFor="graph-search">Search documents</label>
          <input
            id="graph-search" type="search" className="field field-sm"
            placeholder="Filter documents…" value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        </form>

        <div className="tb-layout" role="group" aria-label="Graph layout">
          {LAYOUTS.map((l) => (
            <button
              key={l.id}
              className={`btn btn-sm ${layout === l.id ? 'btn-on' : ''}`}
              onClick={() => setLayout(l.id)}
              aria-pressed={layout === l.id}
            >
              {l.name}
            </button>
          ))}
        </div>

        <span className="tb-count" title="Double-click a node, or use Expand in the inspector, to grow the graph">
          {topo.data ? `${topo.data.total_nodes} nodes · ${topo.data.total_edges} edges (seed)` : '—'}
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
            <h3>No nodes match</h3>
            <p className="muted small">Clear the search or re-enable a node type.</p>
            <button className="btn" onClick={() => { setSearch(''); setDraft(''); setLabels(ALL_LABELS); }}>
              Reset filters
            </button>
          </div>
        )}

        {!topo.loading && !topo.error && topo.data && topo.data.nodes.length > 0 && (
          <GraphCanvas
            ref={canvasRef}
            topology={topo.data} layout={layout}
            selectedId={selected} onSelect={setSelected}
          />
        )}

        {selected && (
          <NodeInspector nodeId={selected} onClose={() => setSelected(null)} onExpand={handleExpand} />
        )}
      </main>

      <GraphLegend />

      <aside className="dash-side">
        <AskPanel
          presetQuestion={preset?.q ?? ''}
          presetId={preset?.id ?? null}
          onClearPreset={() => setPreset(null)}
          onCitations={focusCitations}
        />
        <div className="side-divider" />
        <QuestionPicker
          activeId={preset?.id ?? null}
          onPick={(q, id) => setPreset({ q, id })}
        />
      </aside>
    </div>
  );
}
