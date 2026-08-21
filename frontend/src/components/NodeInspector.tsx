import { useState } from 'react';
import { Network, X, Copy, Check } from 'lucide-react';
import { getNodeDetail } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import type { NodeLabel } from '../lib/types';
import './NodeInspector.css';

interface Props {
  nodeId: string;
  workspaceId?: string | null;
  onClose: () => void;
  onExpand: (nodeId: string, label: NodeLabel) => Promise<void>;
}

/* One line per node type, so the card says what you're looking at rather than
 * leaving you to infer it from a coloured dot. */
const WHAT_IS_IT: Record<string, string> = {
  Document: 'A source document ingested from one of nine enterprise systems.',
  Person: 'A person mentioned across documents. Aliases are bridged with SAME_AS.',
  Org: 'An organisation referenced in the corpus.',
  Ticket: 'A ticket or issue referenced by a document.',
  Project: 'A project or pull request referenced by a document.',
  Fact: 'An atomic assertion extracted from a document: subject, attribute, value.',
  Metric: 'A metric or configuration key a document references.',
  Topic: 'A subject a document is about. Topics are how unrelated documents turn out to be connected.',
};

const REL_MEANING: Record<string, string> = {
  MENTIONS: 'this document mentions',
  HAS_FACT: 'asserted by',
  SAME_AS: 'same person as',
  SUPERSEDES: 'supersedes',
};

export default function NodeInspector({ nodeId, workspaceId, onClose, onExpand }: Props) {
  const { data, loading, error } = useAsync((s) => getNodeDetail(nodeId, workspaceId, s), [nodeId, workspaceId]);
  const [expanding, setExpanding] = useState(false);
  const [copied, setCopied] = useState(false);

  async function handleExpand() {
    if (!data || expanding) return;
    setExpanding(true);
    try {
      await onExpand(nodeId, data.label as NodeLabel);
    } finally {
      setExpanding(false);
    }
  }

  function copyId() {
    const id = data?.doc_id || data?.id || '';
    navigator.clipboard?.writeText(id).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1400);
    }).catch(() => {});
  }

  const facts = data?.facts ?? [];

  // Group neighbours by relationship so five separate MENTIONS rows become one
  // labelled group naming five people. HAS_FACT neighbours ARE the facts already
  // rendered above, so including them printed every fact twice — once as a
  // readable attribute/value row and once as a chip repeating the raw triple.
  const grouped = new Map<string, { id: string; name: string; label: string }[]>();
  for (const n of data?.connected_neighbors ?? []) {
    if (n.relationship === 'HAS_FACT' && facts.length > 0) continue;
    const list = grouped.get(n.relationship) ?? [];
    if (!list.some((x) => x.name === (n.name ?? n.id))) {
      list.push({ id: n.id, name: n.name ?? n.id, label: n.label });
    }
    grouped.set(n.relationship, list);
  }

  return (
    <aside className="inspector panel" aria-label="Node inspector">
      <header className="inspector-head">
        <div className="ins-head-left">
          <span className={`ins-dot ins-dot-${(data?.label ?? 'Document').toLowerCase()}`} aria-hidden="true" />
          <span className="ins-type">{data?.label ?? 'Node'}</span>
        </div>
        <div className="inspector-actions">
          {data && (
            <button className="btn btn-sm" onClick={handleExpand} disabled={expanding} title="Load this node's neighbours onto the canvas">
              <Network size={13} aria-hidden="true" />
              {expanding ? 'Expanding…' : 'Expand'}
            </button>
          )}
          <button className="btn btn-sm btn-icon" onClick={onClose} aria-label="Close inspector">
            <X size={15} aria-hidden="true" />
          </button>
        </div>
      </header>

      {loading && (
        <div className="inspector-body" aria-busy="true">
          <span className="skeleton line-sk" style={{ width: '70%' }} />
          <span className="skeleton line-sk" style={{ width: '90%' }} />
        </div>
      )}

      {error && <p className="alert alert-danger" role="alert">{error}</p>}

      {!loading && data && (
        <div className="inspector-body">
          <h3 className="inspector-name">{data.name}</h3>
          {WHAT_IS_IT[data.label] && <p className="ins-what">{WHAT_IS_IT[data.label]}</p>}

          <div className="ins-meta">
            {data.source && <span className="ins-pill">{data.source}</span>}
            {data.created_at && <span className="ins-pill">{String(data.created_at).slice(0, 10)}</span>}
            {facts.length > 0 && (
              <span className="ins-pill ins-pill-accent">
                {facts.length} {facts.length === 1 ? 'fact' : 'facts'}
              </span>
            )}
            {(data.connected_neighbors?.length ?? 0) > 0 && (
              <span className="ins-pill">
                {data.connected_neighbors.length} {data.connected_neighbors.length === 1 ? 'link' : 'links'}
              </span>
            )}
          </div>

          {/* Facts first: this is what the graph knows, as opposed to what the
            * document merely says. It was previously omitted from the card. */}
          {facts.length > 0 && (
            <section className="ins-section">
              <h4 className="ins-h">What the graph knows</h4>
              <ul className="fact-rows">
                {facts.map((f, i) => (
                  <li key={f.id ?? i}>
                    <span className="fr-attr">{String(f.attribute).replace(/_/g, ' ')}</span>
                    <span className="fr-val">{f.value}</span>
                    {/* On a Document card every fact's subject is the document
                      * itself, which is the heading two lines up. Only worth a
                      * row when it says something new. */}
                    {f.subject && f.subject !== data.name && (
                      <span className="fr-subj">{f.subject}</span>
                    )}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {grouped.size > 0 && (
            <section className="ins-section">
              <h4 className="ins-h">Connected</h4>
              {[...grouped.entries()].map(([rel, items]) => (
                <div key={rel} className="rel-group">
                  <span className="rel-label">{REL_MEANING[rel] ?? rel}</span>
                  <div className="rel-items">
                    {items.slice(0, 10).map((it) => (
                      <span key={it.id} className="rel-chip" title={it.label}>
                        <span className={`ins-dot ins-dot-${it.label.toLowerCase()}`} aria-hidden="true" />
                        {it.name}
                      </span>
                    ))}
                    {items.length > 10 && <span className="rel-more">+{items.length - 10} more</span>}
                  </div>
                </div>
              ))}
            </section>
          )}

          {data.full_body && (
            <details className="body-block">
              <summary>Source text</summary>
              <pre className="body-text">{data.full_body.slice(0, 4000)}</pre>
            </details>
          )}

          {/* The 32-character hash is provenance, not something to read first. */}
          {(data.doc_id || data.id) && (
            <button className="ins-id" onClick={copyId} title="Copy identifier">
              {copied ? <Check size={11} aria-hidden="true" /> : <Copy size={11} aria-hidden="true" />}
              <span className="mono">{data.doc_id || data.id}</span>
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
