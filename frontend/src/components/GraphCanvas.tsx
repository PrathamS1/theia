import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react';
import cytoscape from 'cytoscape';
import type { Core, ElementDefinition, LayoutOptions } from 'cytoscape';
import type { NodeLabel, Topology } from '../lib/types';
import { expandNode as apiExpandNode, ApiError } from '../lib/api';
import './GraphCanvas.css';

export type LayoutName = 'breadthfirst' | 'concentric' | 'grid' | 'cose';

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
    edge: v('--border-strong', '#c9c9c3'),
    accent: v('--accent', '#0f7d76'),
    warn: v('--n-fact-stale', '#9a5b0c'),
    text: v('--text', '#17181a'),
    halo: '#ffffff',
  };
}

function layoutOf(name: LayoutName): LayoutOptions {
  const base = { animate: true, animationDuration: 320, padding: 40, fit: true };
  switch (name) {
    case 'breadthfirst':
      return { ...base, name: 'breadthfirst', spacingFactor: 1.1, circle: false } as LayoutOptions;
    case 'concentric':
      return {
        ...base, name: 'concentric', minNodeSpacing: 24,
        concentric: (n: cytoscape.NodeSingular) => n.degree(false) + 1,
        levelWidth: () => 2,
      } as LayoutOptions;
    case 'grid':
      return { ...base, name: 'grid', avoidOverlap: true } as LayoutOptions;
    case 'cose':
      return { ...base, name: 'cose', nodeRepulsion: () => 9000, idealEdgeLength: () => 90 } as LayoutOptions;
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
  const [expandError, setExpandError] = useState<string | null>(null);

  useEffect(() => { layoutRef.current = layout; }, [layout]);

  // Rebuild from scratch whenever the seed topology changes (filter/search/
  // doc-limit change) -- everything grafted via expand() is intentionally
  // reset along with it.
  useEffect(() => {
    if (!boxRef.current) return;
    const p = readPalette();
    expandedRef.current = new Set();

    const elements: ElementDefinition[] = [
      ...topology.nodes.map((n) => ({ data: { ...n.data } })),
      ...topology.edges.map((e) => ({ data: { ...e.data } })),
    ];

    const cy = cytoscape({
      container: boxRef.current,
      elements,
      minZoom: 0.15,
      maxZoom: 3,
      wheelSensitivity: 0.25,
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
            'font-size': '9px',
            'font-family': 'system-ui, sans-serif',
            'text-valign': 'bottom',
            'text-margin-y': 4,
            'text-max-width': '110px',
            'text-wrap': 'ellipsis',
            'text-outline-color': p.halo,
            'text-outline-width': 2,
            width: 18, height: 18,
            'border-width': 0,
            'transition-property': 'width height border-width',
            'transition-duration': 140,
          },
        },
        {
          /* Superseded facts read as faded — staleness is visible, not just colour-coded. */
          selector: 'node[label = "Fact"][?is_active]',
          style: { width: 22, height: 22 },
        },
        { selector: 'node[is_active = false]', style: { opacity: 0.55, 'border-style': 'dashed', 'border-width': 1.5, 'border-color': p.warn } },
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
        { selector: 'node.expanding', style: {
            'border-width': 2, 'border-color': p.accent, 'border-style': 'dotted',
        } },
        /* Already-explored nodes get a faint solid ring, distinct from the
         * thicker/coloured .sel ring, so double-clicking again reads as a
         * no-op rather than silently doing nothing. */
        { selector: 'node.expanded', style: {
            'border-width': 1.5, 'border-color': p.edge, 'border-style': 'solid', 'border-opacity': 0.6,
        } },
        { selector: '.dim', style: { opacity: 0.15 } },
      ],
      layout: layoutOf(layout),
    });

    cy.on('tap', 'node', (evt) => onSelect(evt.target.id()));
    cy.on('tap', (evt) => { if (evt.target === cy) onSelect(null); });
    // Double-click as a fast path to the same expand action NodeInspector offers.
    cy.on('dblclick', 'node', (evt) => {
      const n = evt.target;
      void handleExpand(n.id(), n.data('label'));
    });

    cyRef.current = cy;
    return () => { cy.destroy(); cyRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [topology, onSelect]);

  /* Re-run layout without rebuilding the graph. */
  useEffect(() => {
    cyRef.current?.layout(layoutOf(layout)).run();
  }, [layout]);

  /* Selection highlight, applied as a class so it survives layout changes. */
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass('sel dim');
      if (!selectedId) return;
      const node = cy.getElementById(selectedId);
      if (node.empty()) return;
      const keep = node.closedNeighborhood();
      cy.elements().difference(keep).addClass('dim');
      node.addClass('sel');
    });
  }, [selectedId, topology]);

  async function handleExpand(nodeId: string, label: NodeLabel) {
    const cy = cyRef.current;
    if (!cy || expandedRef.current.has(nodeId)) return;
    const node = cy.getElementById(nodeId);
    if (node.empty()) return;

    node.addClass('expanding');
    try {
      const result = await apiExpandNode(nodeId, label, workspaceId);
      expandedRef.current.add(nodeId);
      node.addClass('expanded');

      cy.batch(() => {
        const added: cytoscape.ElementDefinition[] = [];
        for (const n of result.nodes) {
          if (cy.getElementById(n.data.id).empty()) added.push({ data: { ...n.data } });
        }
        for (const e of result.edges) {
          if (cy.getElementById(e.data.id).empty()) {
            const srcExists = !cy.getElementById(e.data.source).empty() || added.some((a) => a.data.id === e.data.source);
            const tgtExists = !cy.getElementById(e.data.target).empty() || added.some((a) => a.data.id === e.data.target);
            if (srcExists && tgtExists) added.push({ data: { ...e.data } });
          }
        }
        cy.add(added);
      });

      cy.layout(layoutOf(layoutRef.current)).run();
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Could not expand this node.';
      setExpandError(msg);
      window.setTimeout(() => setExpandError(null), 4000);
    } finally {
      node.removeClass('expanding');
    }
  }

  useImperativeHandle(ref, () => ({
    expandNode: handleExpand,
    fit: () => cyRef.current?.fit(undefined, 40),
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), []);

  return (
    <div className="graph-canvas">
      <div ref={boxRef} className="graph-box" role="application"
           aria-label="Knowledge graph. Click a node to inspect it, double-click to expand its neighbours." />
      <div className="graph-tools">
        <button className="btn btn-sm" onClick={() => cyRef.current?.fit(undefined, 40)}>Fit</button>
        <button className="btn btn-sm" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() * 1.3)}
                aria-label="Zoom in">+</button>
        <button className="btn btn-sm" onClick={() => cyRef.current?.zoom(cyRef.current.zoom() / 1.3)}
                aria-label="Zoom out">&minus;</button>
      </div>
      {expandError && (
        <div className="graph-toast" role="alert">{expandError}</div>
      )}
    </div>
  );
});

export default GraphCanvas;
