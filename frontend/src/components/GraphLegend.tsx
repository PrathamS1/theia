import './GraphLegend.css';

const NODES = [
  { name: 'Document', c: 'var(--n-document)' },
  { name: 'Person', c: 'var(--n-person)' },
  { name: 'Fact', c: 'var(--n-fact)' },
  { name: 'Fact (superseded)', c: 'var(--n-fact-stale)' },
  { name: 'Org', c: 'var(--n-org)' },
  { name: 'Ticket', c: 'var(--n-ticket)' },
  { name: 'Project', c: 'var(--n-project)' },
];

export default function GraphLegend() {
  return (
    <div className="legend">
      <ul className="legend-group">
        {NODES.map((n) => (
          <li key={n.name}>
            <span className="swatch" style={{ background: n.c }} aria-hidden="true" />
            {n.name}
          </li>
        ))}
      </ul>
      <ul className="legend-group">
        <li><span className="line line-same" aria-hidden="true" />SAME_AS</li>
        <li><span className="line line-super" aria-hidden="true" />SUPERSEDES</li>
        <li><span className="line" aria-hidden="true" />MENTIONS / HAS_FACT</li>
      </ul>
    </div>
  );
}
