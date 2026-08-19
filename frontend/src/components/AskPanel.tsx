import { useRef, useState } from 'react';
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
          className="field ask-input"
          rows={3}
          value={value}
          placeholder="e.g. What are the default size limits for multipart file uploads?"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) submit(e);
          }}
        />

        {presetId && !text && (
          <p className="preset-note">
            <span className="tag mono">{presetId}</span>
            benchmark question loaded &mdash; the answer will be scored against its gold answer.
            <button type="button" className="linkish" onClick={onClearPreset}>Clear</button>
          </p>
        )}

        <div className="ask-actions">
          <button className="btn btn-primary" type="submit" disabled={busy || !value.trim()}>
            {busy ? 'Querying…' : 'Ask'}
          </button>
          <span className="hint mono">⌘/Ctrl + ⏎</span>
        </div>
      </form>

      {error && (
        <p className="alert alert-danger" role="alert">{error}</p>
      )}

      {busy && (
        <div className="ask-loading" aria-busy="true" aria-label="Running query">
          <span className="skeleton line-sk" style={{ width: '90%' }} />
          <span className="skeleton line-sk" style={{ width: '75%' }} />
          <span className="skeleton line-sk" style={{ width: '82%' }} />
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
