import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useMediaQuery } from '../lib/useMediaQuery';
import './GraphLegend.css';

const NODES = [
  { name: 'Document', c: 'var(--n-document)' },
  { name: 'Person', c: 'var(--n-person)' },
  { name: 'Fact', c: 'var(--n-fact)' },
  { name: 'Fact (superseded)', c: 'var(--n-fact-stale)' },
  { name: 'Org', c: 'var(--n-org)' },
  { name: 'Ticket', c: 'var(--n-ticket)' },
  { name: 'Project', c: 'var(--n-project)' },
  { name: 'Metric', c: 'var(--n-metric)' },
  { name: 'Topic', c: 'var(--n-topic)' },
];

/* Floats over the canvas as a translucent card rather than occupying a full-width
 * strip beneath it — the reference tools all treat legends and controls as chrome
 * layered on the work surface, not as page furniture that steals vertical space.
 * Collapsible because once you know the colours it is pure clutter. */
export default function GraphLegend() {
  /* Open by default only where there is canvas to spare. At 1024x768 the
   * expanded card covered roughly 40% of the graph — the legend explaining the
   * picture was hiding the picture. Below that it starts collapsed; the toggle
   * still works either way, and the user's choice sticks for the session. */
  const roomy = useMediaQuery('(min-width: 1200px)');
  const [open, setOpen] = useState(roomy);

  return (
    <div className={`legend ${open ? 'legend-open' : ''}`}>
      <button
        type="button"
        className="legend-toggle"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <span className="legend-title">Legend</span>
        <ChevronDown size={13} className="legend-chevron" aria-hidden="true" />
      </button>

      {open && (
        <div className="legend-body">
          <ul className="legend-group">
            {NODES.map((n) => (
              <li key={n.name}>
                <span className="swatch" style={{ background: n.c }} aria-hidden="true" />
                {n.name}
              </li>
            ))}
          </ul>
          <ul className="legend-group legend-edges">
            <li><span className="line line-same" aria-hidden="true" />SAME_AS</li>
            <li><span className="line line-super" aria-hidden="true" />SUPERSEDES</li>
            <li><span className="line" aria-hidden="true" />MENTIONS / HAS_FACT</li>
          </ul>
        </div>
      )}
    </div>
  );
}
