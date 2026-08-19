import { Link } from 'react-router-dom';
import { getHealth } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import './Landing.css';

/* Content-first: these are the four failure modes the architecture exists to
 * solve, straight from the project's own framing. */
const FAILURES = [
  {
    problem: 'Identity fragmentation',
    vector: 'Treats @soham, S. Ratnaparkhi and Soham as three unrelated entities.',
    theia: 'SAME_AS edges link handles, emails and legal names with provenance.',
    edge: 'SAME_AS',
  },
  {
    problem: 'Temporal contradiction',
    vector: 'Retrieves an older doc that scores well and reports a stale policy as current.',
    theia: 'SUPERSEDES edges route to the active fact and deprecate the superseded one.',
    edge: 'SUPERSEDES',
  },
  {
    problem: 'Multi-hop blindness',
    vector: 'Misses a chain that runs from an email to a ticket to a pull request.',
    theia: 'Graph traversal walks MENTIONS and HAS_FACT paths across all nine tools.',
    edge: 'MENTIONS',
  },
  {
    problem: 'Ungrounded answers',
    vector: 'Invents a confident answer when the information simply is not there.',
    theia: 'An abstention gate checks path connectivity and declines to answer.',
    edge: 'ABSTAIN',
  },
];

export default function Landing() {
  const { data: health, loading } = useAsync((s) => getHealth(s), []);

  const stats = [
    { label: 'Documents', value: health?.total_documents },
    { label: 'Persons resolved', value: health?.total_persons },
    { label: 'Facts extracted', value: health?.total_facts },
    { label: 'Vectors indexed', value: health?.total_vectors },
  ];

  return (
    <div className="landing">
      <a className="skip-link" href="#main">Skip to content</a>

      <header className="landing-nav">
        <span className="wordmark">Theia</span>
        <Link className="btn btn-sm" to="/dashboard">Open dashboard</Link>
      </header>

      <main id="main">
        <section className="hero">
          <p className="eyebrow">Graph-augmented enterprise intelligence</p>
          <h1>
            Your company&rsquo;s knowledge,
            <br />
            connected and current.
          </h1>
          <p className="lede">
            Theia answers questions across Slack, Gmail, Linear, Jira, GitHub, Confluence,
            Drive, HubSpot and Fireflies &mdash; resolving who is who, preferring the fact
            that is still true, and declining to answer when the evidence is not there.
          </p>
          <div className="hero-actions">
            <Link className="btn btn-primary" to="/dashboard">Explore the graph</Link>
            <a className="btn" href="/docs" target="_blank" rel="noreferrer">API reference</a>
          </div>

          <dl className="stats" aria-busy={loading}>
            {stats.map((s) => (
              <div key={s.label} className="stat">
                <dt>{s.label}</dt>
                <dd>
                  {loading ? <span className="skeleton stat-skeleton" />
                    : s.value != null ? s.value.toLocaleString() : '—'}
                </dd>
              </div>
            ))}
          </dl>
          {health && (
            <p className={`conn ${health.hydradb_connected ? 'conn-ok' : 'conn-off'}`}>
              <span className="dot" aria-hidden="true" />
              {health.hydradb_connected
                ? 'HydraDB connected — graph traversal active'
                : 'HydraDB offline — answers fall back to vector and lexical retrieval'}
            </p>
          )}
        </section>

        <section className="failures" aria-labelledby="failures-h">
          <h2 id="failures-h">Where flat vector search breaks down</h2>
          <ul className="failure-list">
            {FAILURES.map((f) => (
              <li key={f.problem} className="failure">
                <div className="failure-head">
                  <h3>{f.problem}</h3>
                  <span className="tag mono">{f.edge}</span>
                </div>
                <p className="failure-vector">
                  <span className="label-inline">Vector RAG</span>{f.vector}
                </p>
                <p className="failure-theia">
                  <span className="label-inline">Theia</span>{f.theia}
                </p>
              </li>
            ))}
          </ul>
        </section>
      </main>

      <footer className="landing-foot">
        <span>Theia &middot; built on HydraDB</span>
        <Link to="/dashboard">Open dashboard &rarr;</Link>
      </footer>
    </div>
  );
}
