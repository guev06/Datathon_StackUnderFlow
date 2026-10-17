import type { RepoGraph } from '../../lib/types';

type Props = {
  graph: RepoGraph;
  colors: Record<string, string>;
  hidden: Set<string>;
  query: string;
  selected: string | null;
  onQuery: (q: string) => void;
  onToggleGroup: (g: string) => void;
  onSelect: (id: string) => void;
};

export default function Sidebar({ graph, colors, hidden, query, selected, onQuery, onToggleGroup, onSelect }: Props) {
  const groups = Object.keys(colors);
  const q = query.toLowerCase();
  const files = graph.files.filter((f) => !hidden.has(f.group) && f.path.toLowerCase().includes(q));

  return (
    <aside className="sidebar">
      <div className="sb-section">
        <div className="sb-repo">
          <span className="mono">{graph.owner}/{graph.repo}</span>
          <span className="sb-branch mono">{graph.branch}</span>
        </div>
        <div className="sb-stats">
          <span><strong>{graph.files.length}</strong> files</span>
          <span><strong>{graph.edges.length}</strong> connections</span>
        </div>
        {graph.source === 'demo' && <p className="sb-note">Showing a demo repository.</p>}
        {graph.truncated && <p className="sb-note">Large repo — showing the first {graph.files.length} files.</p>}
      </div>

      <div className="sb-section">
        <span className="eyebrow">Modules</span>
        <ul className="sb-groups">
          {groups.map((g) => (
            <li key={g}>
              <button className={hidden.has(g) ? 'off' : ''} onClick={() => onToggleGroup(g)}>
                <span className="sb-swatch" style={{ background: colors[g] }} />
                <span className="mono">{g}</span>
                <span className="sb-count">{graph.files.filter((f) => f.group === g).length}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="sb-section sb-files">
        <input className="sb-search mono" placeholder="Filter files…" value={query} onChange={(e) => onQuery(e.target.value)} />
        <ul>
          {files.map((f) => (
            <li key={f.id}>
              <button className={f.id === selected ? 'on' : ''} onClick={() => onSelect(f.id)} title={f.path}>
                <span className="sb-swatch" style={{ background: colors[f.group] }} />
                <span className="mono sb-file">{f.path}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </aside>
  );
}
