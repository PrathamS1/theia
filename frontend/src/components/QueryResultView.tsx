import type { QueryResult } from '../lib/types';

/* The engine composes its answer extractively: non-superseded graph facts first,
 * then the best passage from each cited document, joined by blank lines. Rendering
 * that as one blob buries the distinction between a fact resolved out of HydraDB
 * and raw source text. Splitting it back apart costs nothing and makes the
 * provenance legible.
 *
 * Anything that matches neither shape is passed through untouched — this is a
 * presentation layer, and it must never silently drop part of an answer. */
type Block =
  | { kind: 'fact'; text: string }
  | { kind: 'passage'; docId: string; text: string }
  | { kind: 'text'; text: string };

/* Split on the markers themselves rather than on blank lines: source passages
 * routinely contain their own blank lines (they are raw Slack threads, tables and
 * changelogs), and splitting on those detaches a passage's tail from its doc id. */
const MARKER_RE = /^(?:Fact: |Passage \(([^)]+)\): ?)/gm;

function parseAnswer(answer: string): Block[] {
  const src = answer.replace(/\r\n/g, '\n');
  const marks: { index: number; length: number; docId?: string }[] = [];

  MARKER_RE.lastIndex = 0;
  for (let m = MARKER_RE.exec(src); m !== null; m = MARKER_RE.exec(src)) {
    marks.push({ index: m.index, length: m[0].length, docId: m[1] });
  }

  // No markers at all (or a leading preamble) — hand it back verbatim.
  if (marks.length === 0) {
    const t = src.trim();
    return t ? [{ kind: 'text', text: t }] : [];
  }

  const blocks: Block[] = [];
  const preamble = src.slice(0, marks[0].index).trim();
  if (preamble) blocks.push({ kind: 'text', text: preamble });

  marks.forEach((mk, i) => {
    const end = i + 1 < marks.length ? marks[i + 1].index : src.length;
    const body = src.slice(mk.index + mk.length, end).trim();
    if (!body) return;
    blocks.push(mk.docId ? { kind: 'passage', docId: mk.docId, text: body } : { kind: 'fact', text: body });
  });

  return blocks;
}

function AnswerBody({ answer }: { answer: string }) {
  const blocks = parseAnswer(answer);
  const facts = blocks.filter((b): b is Extract<Block, { kind: 'fact' }> => b.kind === 'fact');
  const rest = blocks.filter((b) => b.kind !== 'fact');

  return (
    <div className="answer">
      <h3>Answer</h3>

      {facts.length > 0 && (
        <div className="ans-facts">
          <h4 className="ans-sub">
            Resolved from the graph
            <span className="ans-count">{facts.length}</span>
          </h4>
          <ul className="fact-list">
            {facts.map((f, i) => (
              <li key={i}>{f.text}</li>
            ))}
          </ul>
        </div>
      )}

      {rest.length > 0 && (
        <div className="ans-passages">
          {facts.length > 0 && <h4 className="ans-sub">Supporting passages</h4>}
          {rest.map((b, i) =>
            b.kind === 'passage' ? (
              <figure className="passage" key={i}>
                <blockquote>{b.text}</blockquote>
                <figcaption className="mono">{b.docId}</figcaption>
              </figure>
            ) : (
              <p key={i}>{b.text}</p>
            ),
          )}
        </div>
      )}
    </div>
  );
}

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
        <AnswerBody answer={result.answer} />
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

      {result.trace?.snapshot && (
        <details className="result-block">
          <summary>Graph proof</summary>
          <dl className="proof">
            <dt>Read epoch</dt>
            <dd className="mono">{result.trace.snapshot.read_epoch ?? '—'}</dd>
            <dt>Bookmark</dt>
            <dd className="mono proof-bookmark">{result.trace.snapshot.bookmark}</dd>
            <dt>Executed Cypher</dt>
            <dd><pre className="proof-cypher">{result.trace.snapshot.cypher}</pre></dd>
          </dl>
          <p className="muted small">
            The bookmark pins the immutable HydraDB epoch this answer was read from,
            so the same query can be replayed against the exact graph state that produced it.
          </p>
        </details>
      )}
    </div>
  );
}
