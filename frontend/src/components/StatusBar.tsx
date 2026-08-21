import { Link } from 'react-router-dom';
import type { EvalLatest, Health } from '../lib/types';
import './StatusBar.css';

interface Props {
  health: Health | null;
  healthError: string | null;
  evalData: EvalLatest | null;
}

export default function StatusBar({ health, healthError, evalData }: Props) {
  const connected = health?.hydradb_connected ?? false;

  return (
    <header className="statusbar">
      <div className="sb-left">
        <Link to="/" className="wordmark sb-mark">Theia</Link>
        <span className="sb-sub">Company brain</span>
      </div>

      <div className="sb-stats">
        {healthError ? (
          <span className="sb-conn sb-off" role="alert">
            <span className="dot" aria-hidden="true" />API unreachable
          </span>
        ) : (
          <>
            <span className={`sb-conn ${connected ? 'sb-ok' : 'sb-off'}`}>
              <span className="dot" aria-hidden="true" />
              {connected ? 'HydraDB connected' : 'HydraDB offline'}
            </span>
            {health && (
              <>
                <Stat label="docs" value={health.total_documents} />
                <Stat label="persons" value={health.total_persons} />
                <Stat label="facts" value={health.total_facts} />
                <Stat label="vectors" value={health.total_vectors} />
              </>
            )}
            {evalData && (
              <span className="sb-score" title="Documented EnterpriseRAG-Bench composite score">
                bench <strong>{evalData.summary.overall_composite_score}</strong>
              </span>
            )}
          </>
        )}
      </div>
    </header>
  );
}

/* `value` is null while a count has not been measured yet: on a large graph the
 * label scans are slow, so /api/health serves the counts it has and refreshes the
 * rest in the background rather than blocking the page. Render an em dash for the
 * ones still pending -- "not measured" is not "zero". */
function Stat({ label, value }: { label: string; value: number | null | undefined }) {
  const shown = typeof value === 'number' ? value.toLocaleString() : '—';
  return (
    <span className="sb-stat">
      <strong>{shown}</strong>
      {label}
    </span>
  );
}
