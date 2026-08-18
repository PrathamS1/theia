import { useState } from 'react';
import { getNodeDetail } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import type { NodeLabel } from '../lib/types';
import './NodeInspector.css';

interface Props {
  nodeId: string;
  onClose: () => void;
  onExpand: (nodeId: string, label: NodeLabel) => Promise<void>;
}

export default function NodeInspector({ nodeId, onClose, onExpand }: Props) {
  const { data, loading, error } = useAsync((s) => getNodeDetail(nodeId, s), [nodeId]);
  const [expanding, setExpanding] = useState(false);

  async function handleExpand() {
    if (!data || expanding) return;
    setExpanding(true);
    try {
      await onExpand(nodeId, data.label as NodeLabel);
    } finally {
      setExpanding(false);
    }
  }

  return (
    <aside className="inspector panel" aria-label="Node inspector">
      <header className="inspector-head">
        <span className="tag">{data?.label ?? 'Node'}</span>
        <div className="inspector-actions">
          {data && (
            <button className="btn btn-sm" onClick={handleExpand} disabled={expanding}>
              {expanding ? 'Expanding…' : 'Expand'}
            </button>
          )}
          <button className="btn btn-sm" onClick={onClose} aria-label="Close inspector">Close</button>
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

          <dl className="props">
            {Object.entries(data.properties ?? {})
              .filter(([, v]) => v !== '' && v != null)
              .map(([k, v]) => (
                <div key={k} className="prop">
                  <dt>{k}</dt>
                  <dd className="mono">{String(v)}</dd>
                </div>
              ))}
          </dl>

          {data.full_body ? (
            <details className="body-block">
              <summary>Source text</summary>
              <pre className="body-text">{data.full_body.slice(0, 4000)}</pre>
            </details>
          ) : (
            <p className="muted small">No source text available for this node.</p>
          )}

          {data.connected_neighbors?.length > 0 && (
            <div className="neighbors">
              <h4>Connected</h4>
              <ul>
                {data.connected_neighbors.map((n) => (
                  <li key={n.id}>
                    <span className="tag">{n.relationship}</span>
                    <span className="mono small">{n.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}
