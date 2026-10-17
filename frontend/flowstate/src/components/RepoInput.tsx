import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './RepoInput.css';

export default function RepoInput({ initial = '', compact = false }: { initial?: string; compact?: boolean }) {
  const [value, setValue] = useState(initial);
  const navigate = useNavigate();

  function submit(e: FormEvent) {
    e.preventDefault();
    const repo = value.trim();
    navigate(repo ? `/explore?repo=${encodeURIComponent(repo)}` : '/explore');
  }

  return (
    <form className={`repo-input${compact ? ' compact' : ''}`} onSubmit={submit}>
      <span className="repo-input-icon" aria-hidden>
        <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
          <path d="M8 0a8 8 0 0 0-2.53 15.59c.4.07.55-.17.55-.38v-1.33c-2.23.48-2.7-1.07-2.7-1.07-.36-.92-.89-1.17-.89-1.17-.73-.5.05-.49.05-.49.8.06 1.23.83 1.23.83.72 1.22 1.87.87 2.33.66.07-.52.28-.87.5-1.07-1.78-.2-3.65-.89-3.65-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82a7.6 7.6 0 0 1 4 0c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.28.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48v2.2c0 .21.15.46.55.38A8 8 0 0 0 8 0Z" />
        </svg>
      </span>
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="github.com/owner/repo"
        aria-label="Repository URL"
        spellCheck={false}
      />
      <button className="btn btn-primary" type="submit">Visualize</button>
    </form>
  );
}
