import { useState } from 'react';
import { Search, Loader2, X } from 'lucide-react';
import { getQuestions } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import { useDebouncedValue } from '../lib/useDebouncedValue';
import './QuestionPicker.css';

interface Props {
  onPick: (question: string, id: string) => void;
  activeId: string | null;
}

export default function QuestionPicker({ onPick, activeId }: Props) {
  const [category, setCategory] = useState('all');
  /* Applied once typing pauses. This was a form that only submitted on Enter,
   * so the field looked inert while you typed into it. */
  const [draft, setDraft] = useState('');
  const search = useDebouncedValue(draft, 350);
  const searchPending = draft !== search;

  const { data, loading, error, reload } = useAsync(
    (s) => getQuestions({ category, search, limit: 40 }, s),
    [category, search],
  );

  return (
    <section className="picker" aria-labelledby="picker-h">
      <h2 id="picker-h" className="picker-h">Benchmark questions</h2>

      <div className="picker-controls">
        <label className="sr-only" htmlFor="pick-cat">Filter by category</label>
        <select
          id="pick-cat" className="field field-sm"
          value={category} onChange={(e) => setCategory(e.target.value)}
        >
          <option value="all">All categories</option>
          {data?.categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>

        <div className="picker-search">
          <label className="sr-only" htmlFor="pick-search">Search questions</label>
          <Search size={14} className="tbs-icon" aria-hidden="true" />
          <input
            id="pick-search" type="text" className="field field-sm tbs-input"
            placeholder="Search…" value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Escape') setDraft(''); }}
          />
          <span className="tbs-trail">
            {searchPending
              ? <Loader2 size={13} className="spin" aria-label="Searching" />
              : draft
                ? (
                  <button type="button" className="tbs-clear" onClick={() => setDraft('')} aria-label="Clear search">
                    <X size={13} aria-hidden="true" />
                  </button>
                )
                : null}
          </span>
        </div>
      </div>

      {loading && (
        <div className="picker-list" aria-busy="true" aria-label="Loading questions">
          {Array.from({ length: 5 }).map((_, i) => (
            <span key={i} className="skeleton q-sk" />
          ))}
        </div>
      )}

      {error && (
        <div className="alert alert-danger" role="alert">
          {error}
          <button className="btn btn-sm" onClick={reload} style={{ marginTop: 'var(--s-2)' }}>
            Retry
          </button>
        </div>
      )}

      {!loading && !error && data && data.questions.length === 0 && (
        <p className="picker-empty" role="status">
          No questions match that filter.
        </p>
      )}

      {!loading && !error && data && data.questions.length > 0 && (
        <>
          <p className="picker-count">
            {data.questions.length} of {data.total} shown
          </p>
          <ul className="picker-list" role="list">
            {data.questions.map((q) => (
              <li key={q.question_id}>
                <button
                  className={`q-btn ${activeId === q.question_id ? 'q-active' : ''}`}
                  onClick={() => onPick(q.question, q.question_id)}
                  aria-pressed={activeId === q.question_id}
                >
                  {/* The question is the content; the id and category are
                    * provenance. Reversing that order — metadata on its own
                    * row above a dimmed, clipped question — is what made these
                    * cards read as filler. */}
                  <span className="q-text">{q.question}</span>
                  <span className="q-head">
                    <span className="mono q-id">{q.question_id.replace('qst_', '')}</span>
                    <span className="q-dot" aria-hidden="true" />
                    <span className="q-type">{q.question_type.replace(/_/g, ' ')}</span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

