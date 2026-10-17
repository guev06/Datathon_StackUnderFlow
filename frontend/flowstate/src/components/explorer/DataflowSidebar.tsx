import { useState } from 'react';
import { ROLE_META, ROLE_ORDER } from '../../lib/roles';
import type { Analysis, Role } from '../../lib/types';

type Props = {
  analysis: Analysis;
  selected: string | null;
  hiddenRoles: Set<Role>;
  showCalls: boolean;
  onToggleRole: (r: Role) => void;
  onToggleCalls: () => void;
  onSelect: (stageId: string) => void;
  onSymbol: (symbolId: string) => void;
};

export default function DataflowSidebar({
  analysis,
  selected,
  hiddenRoles,
  showCalls,
  onToggleRole,
  onToggleCalls,
  onSelect,
  onSymbol,
}: Props) {
  const [query, setQuery] = useState('');
  const { stages, roles, source } = analysis.dataflow;
  const q = query.trim().toLowerCase();
  const matches = q
    ? analysis.symbols.filter((s) => s.name.toLowerCase().includes(q) || s.file.toLowerCase().includes(q)).slice(0, 60)
    : [];

  return (
    <aside className="sidebar">
      <div className="sb-section">
        <div className="sb-repo">
          <span className="mono">
            {analysis.owner}/{analysis.repo}
          </span>
          <span className="sb-branch mono">{analysis.sha.slice(0, 7)}</span>
        </div>
        <div className="sb-stats">
          <span><strong>{analysis.files.length}</strong> files</span>
          <span><strong>{analysis.symbols.length}</strong> symbols</span>
          <span><strong>{stages.length}</strong> steps</span>
        </div>
        <p className="sb-note">
          {source === 'model' ? `Dataflow by ${analysis.engine}` : 'Model output was unusable; built from code roles instead.'}
          {analysis.timings.total ? ` · ${analysis.timings.total}s` : ''}
        </p>
        {analysis.truncated && <p className="sb-note">Large repo — analysed the first {analysis.files.length} files.</p>}
      </div>

      <div className="sb-section">
        <span className="eyebrow">Dataflow steps</span>
        <ol className="sb-stages">
          {stages.map((s, i) => (
            <li key={s.id}>
              <button className={s.id === selected ? 'on' : ''} onClick={() => onSelect(s.id)}>
                <span className="sb-step mono" style={{ background: ROLE_META[s.kind].color }}>{i + 1}</span>
                <span className="sb-stage-title">{s.title}</span>
              </button>
            </li>
          ))}
        </ol>
      </div>

      <div className="sb-section">
        <span className="eyebrow">Roles</span>
        <ul className="sb-groups">
          {ROLE_ORDER.map((r) => (
            <li key={r}>
              <button className={hiddenRoles.has(r) ? 'off' : ''} onClick={() => onToggleRole(r)}>
                <span className="sb-swatch" style={{ background: ROLE_META[r].color }} />
                <span>{ROLE_META[r].label}</span>
                <span className="sb-count">{Object.values(roles).filter((x) => x.role === r).length}</span>
              </button>
            </li>
          ))}
          <li>
            <button className={showCalls ? '' : 'off'} onClick={onToggleCalls}>
              <span className="sb-swatch sb-dash" />
              <span>Call edges</span>
            </button>
          </li>
        </ul>
        <p className="sb-note">Roles come from the ONNX classifier ({analysis.role_model}).</p>
      </div>

      <div className="sb-section sb-files">
        <input className="sb-search mono" placeholder="Find a function…" value={query} onChange={(e) => setQuery(e.target.value)} />
        <ul>
          {matches.map((s) => (
            <li key={s.id}>
              <button onClick={() => onSymbol(s.id)} title={`${s.file}:${s.line}`}>
                <span className="sb-swatch" style={{ background: ROLE_META[roles[s.id]?.role ?? 'transform'].color }} />
                <span className="mono sb-file">{s.name}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
