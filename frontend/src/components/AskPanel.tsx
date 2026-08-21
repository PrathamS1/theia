import { useEffect, useRef, useState } from 'react';
import { Sparkles, Loader2, X } from 'lucide-react';
import { runQuery } from '../lib/api';
import type { QueryResult } from '../lib/types';
import QueryResultView from './QueryResultView';
import './AskPanel.css';

interface Props {
  presetQuestion: string;
  presetId: string | null;
  workspaceId?: string | null;
  onClearPreset: () => void;
  onCitations: (docIds: string[]) => void;
}

export default function AskPanel({ presetQuestion, presetId, workspaceId, onClearPreset, onCitations }: Props) {
  const [text, setText] = useState('');
  const [result, setResult] = useState<QueryResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const acRef = useRef<AbortController | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  /* Loading a benchmark question put 200+ characters into a fixed 3-row box, so
   * the question you had just picked was hidden behind a scrollbar. The field
   * now grows to its content up to a cap, after which it scrolls. */
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    // scrollHeight covers content + padding but NOT the border, so assigning it
    // directly to a border-box element leaves the field 2px short and Chrome
    // draws a scrollbar on a textarea that has not actually overflowed.
    const borders = el.offsetHeight - el.clientHeight;
    el.style.height = `${el.scrollHeight + borders}px`;
  }, [text, presetQuestion]);

  /* The pipeline runs server-side, so there is no honest per-stage progress to
   * report. Elapsed time is real, and it is what turns a frozen skeleton into
   * something that visibly reads as still working. */
  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!busy) return;
    setElapsed(0);
    const t0 = performance.now();
    const id = window.setInterval(() => setElapsed(performance.now() - t0), 100);
    return () => window.clearInterval(id);
  }, [busy]);

  /* A preset chosen in the picker wins until the user edits the box. */
  const value = text || presetQuestion;
  const boundId = text ? null : presetId;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const q = value.trim();
    if (!q || busy) return;

    acRef.current?.abort();
    const ac = new AbortController();
    acRef.current = ac;

    setBusy(true);
    setError(null);
    try {
      const r = await runQuery(q, boundId, workspaceId, ac.signal);
      setResult(r);
      onCitations(r.citations);
    } catch (err) {
      if ((err as Error).name !== 'AbortError') setError((err as Error).message);
    } finally {
      if (!ac.signal.aborted) setBusy(false);
    }
  }

  return (
    <section className="ask" aria-labelledby="ask-h">
      <h2 id="ask-h" className="ask-h">Ask the company brain</h2>

      <form onSubmit={submit}>
        <label className="sr-only" htmlFor="ask-input">Your question</label>
        <textarea
          id="ask-input"
          ref={inputRef}
          className="field ask-input"
          rows={2}
          value={value}
          placeholder="e.g. What are the default size limits for multipart file uploads?"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(e);
          }}
        />

        {/* One row, not a mono chip stacked over a sentence stacked over an
          * underlined link. It is a status marker on the field above it, so it
          * reads as an attachment to that field rather than as body copy. */}
        {presetId && !text && (
          <div className="preset-note" role="status">
            <span className="pn-dot" aria-hidden="true" />
            <span className="mono pn-id">{presetId}</span>
            <span className="pn-label">scored against its gold answer</span>
            <button
              type="button"
              className="pn-clear"
              onClick={onClearPreset}
              aria-label={`Clear benchmark question ${presetId}`}
            >
              <X size={12} aria-hidden="true" />
            </button>
          </div>
        )}

        <div className="ask-actions">
          <button className="btn btn-primary ask-btn" type="submit" disabled={busy || !value.trim()}>
            {busy
              ? <Loader2 size={14} className="spin" aria-hidden="true" />
              : <Sparkles size={14} aria-hidden="true" />}
            {busy ? 'Querying…' : 'Ask'}
          </button>
          <span className="hint mono">⌘/Ctrl + ⏎</span>
        </div>
      </form>

      {error && (
        <p className="alert alert-danger" role="alert">{error}</p>
      )}

      {busy && (
        <div className="ask-progress" aria-busy="true" aria-label="Running query">
          <div className="askp-head">
            <Loader2 size={14} className="spin" aria-hidden="true" />
            <span>Retrieving, traversing the graph, composing an answer</span>
            <span className="askp-time mono">{(elapsed / 1000).toFixed(1)}s</span>
          </div>
          <div className="askp-track"><span className="askp-fill" /></div>
        </div>
      )}

      {!busy && !result && !error && (
        <div className="ask-empty" role="status">
          <p>No query yet.</p>
          <p className="muted">
            Ask anything above, or load one of the 500 benchmark questions to compare
            Theia&rsquo;s answer against the documented gold answer.
          </p>
        </div>
      )}

      {!busy && result && <QueryResultView result={result} />}
    </section>
  );
}
