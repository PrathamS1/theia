import type { QueryResult } from '../lib/types';

/* Renders the answer plus the evidence trail. Abstention is deliberately
 * styled as a distinct, legitimate outcome rather than an error. */
export default function QueryResultView({ result }: { result: QueryResult }) {
  const hit =
    result.expected_doc_ids?.length > 0 &&
    result.citations.some((c) => result.expected_doc_ids.includes(c));

  return (
    <div className="result">
      <div className="result-meta">
        <span className="tag">{result.category}</span>
        <span className="tag mono">{Math.round(result.latency_ms)} ms</span>
        {result.abstained
          ? <span className="tag tag-warn">abstained</span>
          : <span className="tag tag-ok">answered</span>}
        {result.expected_doc_ids?.length > 0 && (
          <span className={`tag ${hit ? 'tag-ok' : 'tag-danger'}`}>
            {hit ? 'gold doc retrieved' : 'gold doc missed'}
          </span>
        )}
      </div>

      {result.abstained ? (
        <div className="abstain">
          <h3>No grounded answer</h3>
          <p>{result.answer}</p>
          <p className="muted small">
            The abstention gate found no connected evidence path, so Theia declined
            rather than guessing.
          </p>
        </div>
      ) : (
        <div className="answer">
          <h3>Answer</h3>
          <p>{result.answer}</p>
        </div>
      )}

      {result.citations.length > 0 && (
        <section className="result-block">
          <h3>Citations</h3>
          <ul className="cite-list">
            {result.citations.map((c) => (
              <li key={c} className="mono">{c}</li>
            ))}
          </ul>
        </section>
      )}

      {result.gold_answer && (
        <details className="result-block">
          <summary>Gold answer</summary>
          <p className="gold">{result.gold_answer}</p>
          {result.expected_doc_ids.length > 0 && (
            <ul className="cite-list">
              {result.expected_doc_ids.map((d) => (
                <li key={d} className="mono">{d}</li>
              ))}
            </ul>
          )}
        </details>
      )}

      {result.trace?.vector_anchors?.length > 0 && (
        <details className="result-block">
          <summary>Retrieval trace</summary>
          <ul className="trace-list">
            {result.trace.vector_anchors.map((a) => (
              <li key={a.doc_id}>
                <span className="mono trace-id">{a.doc_id}</span>
                <span className="muted small">vector anchor</span>
              </li>
            ))}
          </ul>
          {result.trace.traversed_entities?.length > 0 && (
            <p className="muted small">
              Traversed entities: {result.trace.traversed_entities.join(', ')}
            </p>
          )}
        </details>
      )}
    </div>
  );
}
