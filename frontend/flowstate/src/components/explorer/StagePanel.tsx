import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import { githubUrl } from '../../lib/analyze';
import { displayName, KIND_ICON, ROLE_META } from '../../lib/roles';
import type { Analysis, CodeSymbol, RepoGraph } from '../../lib/types';

const PREVIEW_LINES = 60;

type Props = {
  graph: RepoGraph;
  analysis: Analysis;
  stageId: string | null;
  symbolId: string | null;
  onStage: (id: string) => void;
  onSymbol: (id: string) => void;
  onOpenFile: (path: string, line: number, end?: number) => void;
  onClose: () => void;
};

function SymbolCode({
  graph,
  analysis,
  symbol,
  active,
  onSymbol,
  onOpenFile,
}: {
  graph: RepoGraph;
  analysis: Analysis;
  symbol: CodeSymbol;
  active: boolean;
  onSymbol: (id: string) => void;
  onOpenFile: (path: string, line: number, end?: number) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const file = analysis.files.find((f) => f.path === symbol.file);
  const lines = useMemo(() => (file?.content ?? '').split('\n').slice(symbol.line - 1, symbol.end_line), [file, symbol]);
  const shown = expanded ? lines : lines.slice(0, PREVIEW_LINES);
  const role = analysis.dataflow.roles[symbol.id];
  const byId = new Map(analysis.symbols.map((s) => [s.id, s]));
  const calls = analysis.calls.filter((c) => c.source === symbol.id).map((c) => byId.get(c.target)!).filter(Boolean);
  const callers = analysis.calls.filter((c) => c.target === symbol.id).map((c) => byId.get(c.source)!).filter(Boolean);

  return (
    <section className={`sym-card${active ? ' on' : ''}`} data-symbol={symbol.id}>
      <header className="sym-head">
        <div className="sym-title">
          <span className="mono sym-name">
            <span className="chip-kind">{KIND_ICON[symbol.kind]}</span> {displayName(symbol)}
          </span>
          <span className="mono sym-loc">
            {symbol.file}:{symbol.line}–{symbol.end_line}
          </span>
        </div>
        <div className="sym-actions">
          {role && (
            <span className="role-pill" style={{ '--node-color': ROLE_META[role.role].color } as CSSProperties} title="ONNX role classifier">
              {ROLE_META[role.role].label} · {Math.round(role.confidence * 100)}%
            </span>
          )}
          <button className="btn btn-ghost sym-btn" onClick={() => onOpenFile(symbol.file, symbol.line, symbol.end_line)}>
            Full file
          </button>
          <a className="btn btn-ghost sym-btn" href={githubUrl(graph, symbol.file, symbol.line)} target="_blank" rel="noreferrer">
            GitHub ↗
          </a>
        </div>
      </header>
      {symbol.doc && <p className="sym-doc">{symbol.doc}</p>}
      {(calls.length > 0 || callers.length > 0) && (
        <div className="sym-links">
          {calls.length > 0 && (
            <div className="cp-row">
              <span className="eyebrow">Calls</span>
              <div className="chips">
                {calls.slice(0, 12).map((s) => (
                  <button key={s.id} className="chip mono" onClick={() => onSymbol(s.id)} title={s.file}>
                    {displayName(s)}
                  </button>
                ))}
              </div>
            </div>
          )}
          {callers.length > 0 && (
            <div className="cp-row">
              <span className="eyebrow">Called by</span>
              <div className="chips">
                {callers.slice(0, 12).map((s) => (
                  <button key={s.id} className="chip mono" onClick={() => onSymbol(s.id)} title={s.file}>
                    {displayName(s)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
      <div className="sym-code mono">
        {shown.map((text, i) => (
          <div key={i} className="cl">
            <button className="cl-n" onClick={() => onOpenFile(symbol.file, symbol.line + i)}>
              {symbol.line + i}
            </button>
            <span className="cl-t">{text || ' '}</span>
          </div>
        ))}
        {lines.length > PREVIEW_LINES && (
          <button className="sym-more" onClick={() => setExpanded((v) => !v)}>
            {expanded ? 'Show less' : `Show ${lines.length - PREVIEW_LINES} more lines`}
          </button>
        )}
      </div>
    </section>
  );
}

export default function StagePanel({ graph, analysis, stageId, symbolId, onStage, onSymbol, onOpenFile, onClose }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { stages, flows } = analysis.dataflow;
  const byId = useMemo(() => new Map(analysis.symbols.map((s) => [s.id, s])), [analysis]);
  const stage = stages.find((s) => s.id === stageId) ?? null;
  const index = stage ? stages.indexOf(stage) : -1;

  // A stage shows all of its code; a lone symbol (e.g. reached via "Calls") shows just that symbol.
  const symbols = stage ? stage.refs.map((r) => byId.get(r)!).filter(Boolean) : symbolId && byId.get(symbolId) ? [byId.get(symbolId)!] : [];
  if (stage && symbolId && !stage.refs.includes(symbolId) && byId.get(symbolId)) symbols.unshift(byId.get(symbolId)!);

  useEffect(() => {
    const el = symbolId ? scrollRef.current?.querySelector<HTMLElement>(`[data-symbol="${CSS.escape(symbolId)}"]`) : null;
    if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' });
    else scrollRef.current?.scrollTo({ top: 0 });
  }, [stageId, symbolId]);

  const incoming = stage ? flows.filter((f) => f.target === stage.id && f.kind === 'flow') : [];
  const outgoing = stage ? flows.filter((f) => f.source === stage.id && f.kind === 'flow') : [];
  const stageTitle = (id: string) => {
    const i = stages.findIndex((s) => s.id === id);
    return `${String(i + 1).padStart(2, '0')} ${stages[i]?.title ?? id}`;
  };
  const meta = stage ? ROLE_META[stage.kind] : null;

  return (
    <aside className="code-panel stage-panel">
      <header className="cp-head">
        <div className="cp-title">
          <span className="cp-swatch" style={{ background: meta?.color ?? 'var(--grad-accent)' }} />
          <div>
            <div className="cp-name">
              {stage ? (
                <>
                  <span className="mono sp-step">Step {index + 1}</span> {stage.title}
                </>
              ) : (
                <span className="mono">{symbols[0] && displayName(symbols[0])}</span>
              )}
            </div>
            <div className="cp-path">{stage ? `${meta!.label} · ${stage.files.join(', ')}` : symbols[0]?.file}</div>
          </div>
        </div>
        <div className="cp-actions">
          {stage && (
            <>
              <button className="btn btn-ghost icon" disabled={index <= 0} onClick={() => onStage(stages[index - 1].id)} aria-label="Previous step">←</button>
              <button className="btn btn-ghost icon" disabled={index >= stages.length - 1} onClick={() => onStage(stages[index + 1].id)} aria-label="Next step">→</button>
            </>
          )}
          <button className="btn btn-ghost icon" onClick={onClose} aria-label="Close">✕</button>
        </div>
      </header>

      {stage && (
        <div className="cp-meta">
          <p className="sp-summary">{stage.summary}</p>
          {incoming.length > 0 && (
            <div className="cp-row">
              <span className="eyebrow">Receives</span>
              <div className="chips">
                {incoming.map((f) => (
                  <button key={f.source} className="chip" onClick={() => onStage(f.source)}>
                    {f.label ? <strong>{f.label}</strong> : null} ← {stageTitle(f.source)}
                  </button>
                ))}
              </div>
            </div>
          )}
          {outgoing.length > 0 && (
            <div className="cp-row">
              <span className="eyebrow">Sends</span>
              <div className="chips">
                {outgoing.map((f) => (
                  <button key={f.target} className="chip" onClick={() => onStage(f.target)}>
                    {f.label ? <strong>{f.label}</strong> : null} → {stageTitle(f.target)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <div className="sp-scroll" ref={scrollRef}>
        {symbols.map((s) => (
          <SymbolCode
            key={s.id}
            graph={graph}
            analysis={analysis}
            symbol={s}
            active={s.id === symbolId}
            onSymbol={onSymbol}
            onOpenFile={onOpenFile}
          />
        ))}
      </div>
    </aside>
  );
}
