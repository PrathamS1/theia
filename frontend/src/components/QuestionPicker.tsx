import { useState } from 'react';
import { getQuestions } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import './QuestionPicker.css';

interface Props {
  onPick: (question: string, id: string) => void;
  activeId: string | null;
}

export default function QuestionPicker({ onPick, activeId }: Props) {
  const [category, setCategory] = useState('all');
  const [search, setSearch] = useState('');
  const [draft, setDraft] = useState('');

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

        <form
          className="picker-search"
          onSubmit={(e) => { e.preventDefault(); setSearch(draft); }}
        >
          <label className="sr-only" htmlFor="pick-search">Search questions</label>
          <input
            id="pick-search" type="search" className="field field-sm"
            placeholder="Search…" value={draft}
            onChange={(e) => setDraft(e.target.value)}
          />
        </form>
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
                  <span className="q-head">
                    <span className="mono q-id">{q.question_id}</span>
                    <span className="tag q-type">{q.question_type}</span>
                  </span>
                  <span className="q-text">{q.question}</span>
                </button>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
