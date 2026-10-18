import { useMemo, type ReactNode } from 'react';
import type { Analysis } from '../../lib/types';

type Props = {
  analysis: Analysis;
  onSymbol: (id: string) => void;
  onFile: (path: string) => void;
};

/** Renders the model's markdown report; `code` spans naming a real function or file become links to that code. */
export default function ReportView({ analysis, onSymbol, onFile }: Props) {
  const lookup = useMemo(() => {
    const symbols = new Map<string, string>();
    for (const s of analysis.symbols) {
      const short = s.name.split('.').pop()!;
      if (!symbols.has(short)) symbols.set(short, s.id);
      symbols.set(s.name, s.id);
    }
    return symbols;
  }, [analysis]);

  function linkFor(code: string): (() => void) | null {
    const name = code.replace(/\(.*\)$/, '').replace(/^.*\./, '').trim();
    const full = code.replace(/\(.*\)$/, '').trim();
    const sym = lookup.get(full) ?? lookup.get(name);
    if (sym) return () => onSymbol(sym);
    const file = analysis.files.find((f) => f.path === code || f.path.endsWith('/' + code));
    if (file) return () => onFile(file.path);
    return null;
  }

  function inline(text: string): ReactNode[] {
    return text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g).map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) return <strong key={i}>{inline(part.slice(2, -2))}</strong>;
      if (part.startsWith('`') && part.endsWith('`')) {
        const code = part.slice(1, -1);
        const go = linkFor(code);
        return go ? (
          <button key={i} className="md-link mono" onClick={go} title="Open in code">
            {code}
          </button>
        ) : (
          <code key={i} className="mono">{code}</code>
        );
      }
      return part;
    });
  }

  const blocks: ReactNode[] = [];
  analysis.report_md.split('\n').forEach((raw, i) => {
    const line = raw.trimEnd();
    if (!line.trim()) return;
    const heading = line.match(/^(#{1,4})\s+(.*)/);
    const item = line.match(/^(\s*)([-*]|\d+\.)\s+(.*)/);
    if (heading) blocks.push(<h3 key={i} className={`md-h md-h${heading[1].length}`}>{inline(heading[2])}</h3>);
    else if (item)
      blocks.push(
        <div key={i} className="md-li" style={{ paddingLeft: 8 + Math.min(item[1].length, 12) * 6 }}>
          <span className="md-bullet mono">{/\d/.test(item[2]) ? item[2] : '•'}</span>
          <span>{inline(item[3])}</span>
        </div>,
      );
    else blocks.push(<p key={i}>{inline(line)}</p>);
  });

  return (
    <div className="report">
      <div className="report-inner">
        <p className="eyebrow">AI dataflow report</p>
        <h2>
          {analysis.owner}/<span className="serif">{analysis.repo}</span>
        </h2>
        <p className="report-meta">
          Written by {analysis.engine} from a structural summary of {analysis.files.length} Python files. Highlighted names link to the code.
        </p>
        <div className="report-body">{blocks}</div>
      </div>
    </div>
  );
}
