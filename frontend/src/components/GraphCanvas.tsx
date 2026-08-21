import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import { Minus, Plus, Maximize2 } from 'lucide-react';
import cytoscape from 'cytoscape';
import type { Core, ElementDefinition, LayoutOptions } from 'cytoscape';
import type { NodeLabel, Topology } from '../lib/types';
import { expandNode as apiExpandNode, ApiError } from '../lib/api';
import './GraphCanvas.css';

/* `breadthfirst` ("Tree") was removed: most documents sit at the same depth, so
 * it drew flat rows and implied a hierarchy the data does not have. */
export type LayoutName = 'concentric' | 'grid' | 'cose';

export interface GraphCanvasHandle {
  /** Fetches a node's 1-hop neighbourhood and grafts it onto the live canvas. */
  expandNode: (nodeId: string, label: NodeLabel) => Promise<void>;
  fit: () => void;
}

interface Props {
  /** The seed subgraph. A new object reference here is treated as a reset
   * (the user changed filters/search/doc count) and rebuilds the canvas from
   * scratch; expand() grafts are appended live and are not reflected back
   * into this prop, so they're intentionally forgotten on reset. */
  topology: Topology;
  layout: LayoutName;
  selectedId: string | null;
  workspaceId?: string | null;
  onSelect: (id: string | null) => void;
}

function readPalette() {
  const css = getComputedStyle(document.documentElement);
  const v = (n: string, fb: string) => css.getPropertyValue(n).trim() || fb;
  return {
    Document: v('--n-document', '#3b6ea5'),
    Person: v('--n-person', '#0f7d76'),
    Fact: v('--n-fact', '#5b7a3f'),
    FactStale: v('--n-fact-stale', '#9a5b0c'),
    Org: v('--n-org', '#7a4a86'),
    Ticket: v('--n-ticket', '#a05a2c'),
    Project: v('--n-project', '#4a7a6a'),
    Metric: v('--n-metric', '#5a6b8c'),
    Topic: v('--n-topic', '#a34a5e'),
    edge: v('--border-strong', '#c9c9c3'),
    accent: v('--accent', '#0f7d76'),
    warn: v('--n-fact-stale', '#9a5b0c'),
    text: v('--text', '#17181a'),
    halo: '#ffffff',
  };
}

// Ceiling for click-to-focus. Framing a node that has a single neighbour would
// otherwise zoom until the two fill the viewport, which reads as a glitch.
const MAX_FOCUS_ZOOM = 1.8;

function layoutOf(name: LayoutName): LayoutOptions {
  const base = { animate: true, animationDuration: 320, padding: 40, fit: true };
  switch (name) {
    case 'concentric':
      return {
        ...base, name: 'concentric', minNodeSpacing: 24,
        concentric: (n: cytoscape.NodeSingular) => n.degree(false) + 1,
        levelWidth: () => 2,
      } as LayoutOptions;
    case 'grid':
      return { ...base, name: 'grid', avoidOverlap: true } as LayoutOptions;
    case 'cose':
      /* `animate: 'end'` rather than `true`. With `true`, cose runs its physics
       * simulation on its OWN requestAnimationFrame loop, which cytoscape's
       * `cy.stop()` does not own and therefore cannot cancel — a frame queued
       * before teardown then calls into a destroyed core and throws
       * "Cannot read properties of null (reading 'notify')". With `'end'` the
       * simulation runs synchronously and the single transition to the final
       * positions is a core-owned animation, which `cy.stop()` does cancel.
       * On graphs this size the synchronous solve is a few milliseconds. */
      return {
        ...base, name: 'cose', animate: 'end',
        nodeRepulsion: () => 9000, idealEdgeLength: () => 90,
      } as LayoutOptions;
  }
}

const GraphCanvas = forwardRef<GraphCanvasHandle, Props>(function GraphCanvas(
  { topology, layout, selectedId, workspaceId, onSelect },
  ref,
) {
  const boxRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const expandedRef = useRef<Set<string>>(new Set());
  const layoutRef = useRef<LayoutName>(layout);
  // Last node the camera was moved to, so a topology refresh does not re-focus.
  const focusedRef = useRef<string | null>(null);
  // Handle on the running layout so it can be stopped before teardown.
  const layoutRunRef = useRef<cytoscape.Layouts | null>(null);
  const [expandError, setExpandError] = useState<string | null>(null);
  /* Non-error outcome of an expand. Distinct from expandError so a successful
   * "nothing new to add" never renders as a failure. */
  const [expandNote, setExpandNote] = useState<string | null>(null);
  // Live zoom readout for the control pill.
  const [zoomPct, setZoomPct] = useState(100);
  /* Hover tooltip. Until now the only way to learn anything about a node was to
   * click it, which on a dense canvas means opening and closing the inspector
   * repeatedly just to find out which dot is which. */
  const [hover, setHover] = useState<
    { x: number; y: number; name: string; label: string; degree: number } | null
  >(null);

  useEffect(() => { layoutRef.current = layout; }, [layout]);

  // Rebuild from scratch whenever the seed topology changes (filter/search/
  // doc-limit change) -- everything grafted via expand() is intentionally
  // reset along with it.
  useEffect(() => {
    if (!boxRef.current) return;
    const p = readPalette();
    expandedRef.current = new Set();
    // The graph is being rebuilt, so whatever the camera was framing is gone.
    // Clearing this lets the current selection re-focus once on the new instance.
    focusedRef.current = null;

    const elements: ElementDefinition[] = [
      ...topology.nodes.map((n) => ({ data: { ...n.data } })),
      ...topology.edges.map((e) => ({ data: { ...e.data } })),
    ];

    const cy = cytoscape({
      container: boxRef.current,
      elements,
      minZoom: 0.15,
      maxZoom: 3,
      // Left at the default: Cytoscape warns that overriding wheel sensitivity
      // makes zoom feel wrong on any mouse other than the developer's own.
      style: [
        {
          selector: 'node',
          style: {
            'background-color': (n: cytoscape.NodeSingular) => {
              const l = n.data('label');
              if (l === 'Fact') return n.data('is_active') === false ? p.FactStale : p.Fact;
              return (p as Record<string, string>)[l] ?? p.Document;
            },
            label: 'data(name)',
            color: p.text,
            // 9px was unreadable on screen and illegible once recorded.
            'font-size': '11px',
            'font-family': 'system-ui, sans-serif',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'text-max-width': '110px',
            'text-wrap': 'ellipsis',
            'text-outline-color': p.halo,
            'text-outline-width': 2,
            width: 18, height: 18,
            'border-width': 0,
            'transition-property': 'width height border-width border-color opacity',
            'transition-duration': 140,
          },
        },
        {
          /* Superseded facts read as faded — staleness is visible, not just colour-coded. */
          selector: 'node[label = "Fact"][?is_active]',
          style: { width: 22, height: 22 },
        },
        /* Cytoscape has no boolean literal in selectors, so `[is_active = false]`
         * was rejected as invalid and this rule never applied -- superseded facts
         * rendered identically to active ones. `[!is_active]` is the falsey test,
         * scoped to Facts so nodes that simply have no is_active are unaffected. */
        { selector: 'node[label = "Fact"][!is_active]', style: { opacity: 0.55, 'border-style': 'dashed', 'border-width': 1.5, 'border-color': p.warn } },
        { selector: 'edge', style: {
            width: 1.2, 'line-color': p.edge, 'target-arrow-color': p.edge,
            'target-arrow-shape': 'triangle', 'arrow-scale': 0.7,
            'curve-style': 'bezier', opacity: 0.75,
        } },
        { selector: 'edge[type = "SAME_AS"]', style: {
            'line-color': p.accent, 'target-arrow-color': p.accent,
            width: 2, 'line-style': 'dashed', opacity: 1,
        } },
        { selector: 'edge[type = "SUPERSEDES"]', style: {
            'line-color': p.warn, 'target-arrow-color': p.warn, width: 2, opacity: 1,
        } },
        { selector: 'node.sel', style: {
            'border-width': 3, 'border-color': p.accent, width: 26, height: 26, 'font-weight': 'bold',
        } },
        /* Hover: the node lifts, its neighbours brighten their connecting edges.
         * Sized just under .sel so a hovered node never outranks the selected one. */
        { selector: 'node.hov', style: {
            width: 24, height: 24, 'border-width': 2, 'border-color': p.accent, 'z-index': 10,
        } },
        { selector: 'node.hov-near', style: { 'border-width': 1.5, 'border-color': p.accent } },
        { selector: 'edge.hov-near', style: { width: 2, opacity: 1, 'line-color': p.accent, 'target-arrow-color': p.accent } },
        { selector: 'node.expanding', style: {
            'border-width': 2, 'border-color': p.accent, 'border-style': 'dotted',
        } },
        /* Already-explored nodes get a faint solid ring, distinct from the
         * thicker/coloured .sel ring, so double-clicking again reads as a
         * no-op rather than silently doing nothing. */
        { selector: 'node.expanded', style: {
            'border-width': 1.5, 'border-color': p.edge, 'border-style': 'solid', 'border-opacity': 0.6,
        } },
        /* Zoomed out, every label overlapping every other label is noise rather
         * than information. Labels fade out below the legibility threshold and the
         * node dots carry the structure; anything the user is actually pointing at
         * or has selected keeps its label at any zoom (rules below win by order). */
        { selector: 'node.nolabel', style: { 'text-opacity': 0 } },
        { selector: 'node.nolabel.sel, node.nolabel.hov', style: { 'text-opacity': 1 } },
        /* Dimmed context stays legible. At 0.15 the rest of the graph effectively
         * vanished on selection, so you lost all sense of where the neighbourhood
         * sat within the whole. Faded, not erased. */
        { selector: '.dim', style: { opacity: 0.32 } },
        /* A hovered node and its neighbours are never dimmed, so hover can reach
         * outside the current selection. */
        { selector: 'node.hov, node.hov-near, edge.hov-near', style: { opacity: 1 } },
      ],
    });

    cy.on('tap', 'node', (evt) => onSelect(evt.target.id()));
    cy.on('tap', (evt) => { if (evt.target === cy) onSelect(null); });

    /* Hover affordance. Feedback lands on pointer-enter, not on click, so the
     * graph reads as touchable before you commit to a node. The neighbourhood
     * lights up rather than the node alone: on a dense canvas the useful signal
     * is "what is this connected to", which is the whole point of the graph.
     * Skipped while a selection is active so hover never fights the .dim state. */
    const container = cy.container();
    cy.on('mouseover', 'node', (evt) => {
      if (cy.destroyed()) return;
      if (container) container.style.cursor = 'pointer';
      // Hover temporarily wins over selection: pointing at another node reveals
      // ITS neighbourhood and reverts on mouse-out. Suppressing hover whenever
      // anything was selected made the graph feel inert exactly when you were
      // trying to explore outward from a result.
      const n = evt.target as cytoscape.NodeSingular;
      n.addClass('hov');
      n.neighborhood().addClass('hov-near');
      const rp = n.renderedPosition();
      setHover({
        x: rp.x,
        y: rp.y,
        name: n.data('name') ?? n.id(),
        label: n.data('label') ?? 'Node',
        // Undirected degree, loops excluded: "how many things is this joined to".
        degree: n.degree(false),
      });
    });
    cy.on('mouseout', 'node', (evt) => {
      if (cy.destroyed()) return;
      if (container) container.style.cursor = '';
      const n = evt.target as cytoscape.NodeSingular;
      n.removeClass('hov');
      n.neighborhood().removeClass('hov-near');
      setHover(null);
    });
    // Panning or zooming moves the node out from under a tooltip pinned to
    // rendered coordinates, so drop it rather than let it drift.
    cy.on('pan zoom drag', () => setHover(null));

    // Label decluttering, re-evaluated on zoom (and once after the first layout).
    const LABEL_ZOOM_MIN = 0.65;
    const applyLabelVisibility = () => {
      // Cytoscape can emit during teardown (and React StrictMode tears the effect
      // down once on mount in dev), so every handler must tolerate a dead instance.
      if (cy.destroyed()) return;
      const hide = cy.zoom() < LABEL_ZOOM_MIN;
      cy.batch(() => {
        if (hide) cy.nodes().addClass('nolabel');
        else cy.nodes().removeClass('nolabel');
      });
    };
    const syncZoom = () => { if (!cy.destroyed()) setZoomPct(Math.round(cy.zoom() * 100)); };
    cy.on('zoom', applyLabelVisibility);
    cy.on('zoom', syncZoom);
    cy.one('layoutstop', syncZoom);
    cy.one('layoutstop', applyLabelVisibility);
    // Double-click as a fast path to the same expand action NodeInspector offers.
    cy.on('dblclick', 'node', (evt) => {
      const n = evt.target;
      void handleExpand(n.id(), n.data('label'));
    });

    cyRef.current = cy;

    // Run the layout ourselves rather than via the constructor's `layout` option,
    // so we hold the instance and can stop it. An animated layout drives its own
    // requestAnimationFrame loop; if the effect tears down mid-animation (React
    // StrictMode does exactly this on mount in dev) the pending frame calls
    // Collection.positions() on a destroyed core and throws
    // "Cannot read properties of null (reading 'notify')".
    const initialLayout = cy.layout(layoutOf(layout));
    layoutRunRef.current = initialLayout;
    initialLayout.run();

    return () => {
      layoutRunRef.current?.stop();
      layoutRunRef.current = null;
      cy.stop();
      cy.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topology, onSelect]);

  /* Re-run layout without rebuilding the graph. */
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    layoutRunRef.current?.stop();
    const run = cy.layout(layoutOf(layout));
    layoutRunRef.current = run;
    run.run();
  }, [layout]);

  /* Selection highlight, applied as a class so it survives layout changes. */
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    cy.batch(() => {
      // Hover classes are cleared too: selecting via keyboard or a citation jump
      // leaves no pointer event to fire mouseout, which would strand a hover ring.
      cy.elements().removeClass('sel dim hov hov-near');
      if (!selectedId) return;
      const node = cy.getElementById(selectedId);
      if (node.empty()) return;
      const keep = node.closedNeighborhood();
      cy.elements().difference(keep).addClass('dim');
      node.addClass('sel');
    });

    // Only move the camera when the *selection* changed. This effect also runs when
    // `topology` changes (filter/search), and animating the viewport then would
    // fight the freshly-started layout animation for control of the same camera.
    const selectionChanged = focusedRef.current !== selectedId;
    focusedRef.current = selectedId;
    if (!selectedId || !selectionChanged) return;

    const node = cy.getElementById(selectedId);
    if (node.empty()) return;
    // Frame the selection's neighbourhood rather than leaving the camera where it
    // was. Deliberately `fit` on the neighbourhood, not a re-fit of the whole
    // graph: re-fitting makes the graph appear to shrink on every click, which is
    // the opposite of zooming in on what you asked about. Capped so a node with
    // one neighbour does not slam to maximum zoom.
    const hood = node.closedNeighborhood();
    cy.stop();
    cy.animate(
      { fit: { eles: hood, padding: 90 } },
      {
        duration: 320,
        easing: 'ease-out',
        complete: () => {
          // The instance can be torn down mid-animation -- a topology refresh
          // rebuilds the graph and destroys this `cy` while the 320ms fit is
          // still in flight. Calling into a destroyed instance throws
          // "Cannot read properties of null (reading 'notify')", which surfaces
          // as an uncaught error in the console and aborts the callback.
          if (cy.destroyed()) return;
          if (cy.zoom() > MAX_FOCUS_ZOOM) {
            cy.zoom({ level: MAX_FOCUS_ZOOM, renderedPosition: node.renderedPosition() });
          }
        },
      },
    );
  }, [selectedId, topology]);

  /* Expand appeared to do nothing, and that was almost always literally true:
   * the seed topology ALREADY pre-expands each document's people, orgs and
   * facts, so a seed document's neighbours are on the canvas before you ever
   * press the button. Every added-node check returned "already present", the
   * call succeeded, and the UI said nothing either way.
   *
   * Two fixes. It now reports what happened in both cases, and when there is
   * nothing new it flashes the existing neighbourhood instead — which is the
   * thing the user was actually asking to see. */
  async function handleExpand(nodeId: string, label: NodeLabel) {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    const node = cy.getElementById(nodeId);
    if (node.empty()) return;

    const flashNeighbourhood = () => {
      const hood = node.neighborhood().add(node);
      hood.addClass('hov-near');
      window.setTimeout(() => { if (!cy.destroyed()) hood.removeClass('hov-near'); }, 1400);
    };

    // Re-pressing an already-expanded node used to return silently.
    if (expandedRef.current.has(nodeId)) {
      flashNeighbourhood();
      const shown = node.degree(false);
      setExpandNote(`Already expanded — ${shown} connection${shown === 1 ? '' : 's'} shown.`);
      window.setTimeout(() => setExpandNote(null), 3000);
      return;
    }

    node.addClass('expanding');
    try {
      const result = await apiExpandNode(nodeId, label, workspaceId);
      expandedRef.current.add(nodeId);
      node.addClass('expanded');

      let addedCount = 0;
      cy.batch(() => {
        const added: cytoscape.ElementDefinition[] = [];
        for (const n of result.nodes) {
          if (cy.getElementById(n.data.id).empty()) added.push({ data: { ...n.data } });
        }
        addedCount = added.length;
        for (const e of result.edges) {
          if (cy.getElementById(e.data.id).empty()) {
            const srcExists = !cy.getElementById(e.data.source).empty() || added.some((a) => a.data.id === e.data.source);
            const tgtExists = !cy.getElementById(e.data.target).empty() || added.some((a) => a.data.id === e.data.target);
            if (srcExists && tgtExists) added.push({ data: { ...e.data } });
          }
        }
        cy.add(added);
      });

      if (addedCount > 0) {
        cy.layout(layoutOf(layoutRef.current)).run();
        setExpandNote(`Added ${addedCount} connected node${addedCount === 1 ? '' : 's'}.`);
      } else {
        // Nothing new: say so, and show what is already there.
        flashNeighbourhood();
        const deg = node.degree(false);
        setExpandNote(
          deg > 0
            ? `All ${deg} connection${deg === 1 ? '' : 's'} are already on the canvas.`
            : 'This node has no further connections in the graph.',
        );
      }
      window.setTimeout(() => setExpandNote(null), 3000);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Could not expand this node.';
      setExpandError(msg);
      window.setTimeout(() => setExpandError(null), 4000);
    } finally {
      node.removeClass('expanding');
    }
  }

  /* Zoom about the viewport centre. cy.zoom(level) scales around the pan origin,
   * which walks the graph off-screen after a few presses. */
  function zoomBy(factor: number) {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    const ext = cy.extent();
    cy.zoom({
      level: cy.zoom() * factor,
      position: { x: (ext.x1 + ext.x2) / 2, y: (ext.y1 + ext.y2) / 2 },
    });
  }

  /* The canvas is a single focusable widget: pan with the arrow keys, zoom with
   * +/-, fit with 0, clear the selection with Escape. This does not make every
   * node individually tabbable -- with thousands of nodes that would be a worse
   * experience than the question picker -- but it does mean the graph is not a
   * pointer-only dead end. */
  function onCanvasKeyDown(e: React.KeyboardEvent<HTMLDivElement>) {
    const cy = cyRef.current;
    if (!cy || cy.destroyed()) return;
    const step = e.shiftKey ? 200 : 60;
    const pans: Record<string, { x: number; y: number }> = {
      ArrowUp: { x: 0, y: step },
      ArrowDown: { x: 0, y: -step },
      ArrowLeft: { x: step, y: 0 },
      ArrowRight: { x: -step, y: 0 },
    };
    if (pans[e.key]) { e.preventDefault(); cy.panBy(pans[e.key]); return; }
    if (e.key === '+' || e.key === '=') { e.preventDefault(); zoomBy(1.3); return; }
    if (e.key === '-' || e.key === '_') { e.preventDefault(); zoomBy(1 / 1.3); return; }
    if (e.key === '0') { e.preventDefault(); cy.fit(undefined, 40); return; }
    if (e.key === 'Escape') { e.preventDefault(); onSelect(null); }
  }

  useImperativeHandle(ref, () => ({
    expandNode: handleExpand,
    fit: () => cyRef.current?.fit(undefined, 40),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), []);

  return (
    <div className="graph-canvas">
      <div
        ref={boxRef}
        className="graph-box"
        role="application"
        tabIndex={0}
        onKeyDown={onCanvasKeyDown}
        aria-label="Knowledge graph. Click a node to inspect it, double-click to expand its neighbours. Arrow keys pan, plus and minus zoom, 0 fits, Escape clears the selection."
      />
      {/* Pinned to rendered coordinates, offset above the node, and
        * pointer-events:none so it can never intercept the click it is
        * advertising. */}
      {hover && (
        <div
          className="graph-tip"
          style={{ left: hover.x, top: hover.y }}
          aria-hidden="true"
        >
          <span className="gtip-name">{hover.name}</span>
          <span className="gtip-meta">
            <span className={`gtip-dot gtip-dot-${hover.label.toLowerCase()}`} />
            {hover.label} · {hover.degree} {hover.degree === 1 ? 'link' : 'links'}
          </span>
        </div>
      )}

      <p className="graph-hint" aria-hidden="true">
        Double-click a node to expand · arrows pan · +/− zoom
      </p>

      {/* One control pill rather than three loose buttons: the zoom readout gives
        * the group a reason to exist and tells you where you are after a
        * click-to-focus jump. */}
      <div className="graph-tools" role="group" aria-label="Canvas controls">
        <button className="gt-btn" onClick={() => zoomBy(1 / 1.3)} aria-label="Zoom out">
          <Minus size={15} aria-hidden="true" />
        </button>
        <span className="gt-zoom" aria-live="polite" aria-label={`Zoom ${zoomPct} percent`}>
          {zoomPct}%
        </span>
        <button className="gt-btn" onClick={() => zoomBy(1.3)} aria-label="Zoom in">
          <Plus size={15} aria-hidden="true" />
        </button>
        <span className="gt-sep" aria-hidden="true" />
        <button
          className="gt-btn gt-fit"
          onClick={() => cyRef.current?.fit(undefined, 40)}
          aria-label="Fit graph to view"
        >
          <Maximize2 size={14} aria-hidden="true" />
          <span>Fit</span>
        </button>
      </div>
      {expandError && (
        <div className="graph-toast graph-toast-error" role="alert">{expandError}</div>
      )}
      {!expandError && expandNote && (
        <div className="graph-toast" role="status">{expandNote}</div>
      )}
    </div>
  );
});

export default GraphCanvas;
