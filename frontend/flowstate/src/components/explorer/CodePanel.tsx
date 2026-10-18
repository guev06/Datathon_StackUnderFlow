import { useEffect, useRef } from "react";
import { githubUrl } from "../../lib/analyze";
import type { FileNode, RepoGraph } from "../../lib/types";

type Props = {
  graph: RepoGraph;
  file: FileNode;
  line: number | null;
  end?: number | null; // highlight line..end, e.g. a whole function opened from the dataflow view
  colors: Record<string, string>;
  onOpen: (path: string, line?: number) => void;
  onClose: () => void;
};

export default function CodePanel({
  graph,
  file,
  line,
  end,
  colors,
  onOpen,
  onClose,
}: Props) {
  const codeRef = useRef<HTMLDivElement>(null);
  const lit = (n: number) =>
    !!line && n >= line && n <= Math.max(end ?? line, line);
  const imports = graph.edges
    .filter((e) => e.source === file.id)
    .map((e) => e.target);
  const importedBy = graph.edges
    .filter((e) => e.target === file.id)
    .map((e) => e.source);

  useEffect(() => {
    const el = codeRef.current?.querySelector<HTMLElement>(
      line ? `[data-line="${line}"]` : '[data-line="1"]',
    );
    el?.scrollIntoView({
      block: line && !end ? "center" : "start",
      behavior: "smooth",
    });
  }, [file.id, line]);

  const Chip = ({ path }: { path: string }) => {
    const f = graph.files.find((x) => x.id === path)!;
    return (
      <button className="chip mono" onClick={() => onOpen(path)} title={path}>
        <span className="chip-dot" style={{ background: colors[f.group] }} />
        {f.label}
      </button>
    );
  };

  return (
    <aside className="code-panel">
      <header className="cp-head">
        <div className="cp-title">
          <span
            className="cp-swatch"
            style={{ background: colors[file.group] }}
          />
          <div>
            <div className="mono cp-name">{file.label}</div>
            <div className="cp-path mono">{file.path}</div>
          </div>
        </div>
        <div className="cp-actions">
          <button
            className="btn btn-ghost icon"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>
      </header>

      <div className="cp-meta">
        {file.symbols.length > 0 && (
          <div className="cp-row">
            <span className="eyebrow">Symbols</span>
            <div className="chips">
              {file.symbols.map((s) => (
                <button
                  key={s.name + s.line}
                  className={`chip mono${line === s.line ? " chip-on" : ""}`}
                  onClick={() => onOpen(file.path, s.line)}
                >
                  <span className="chip-kind">
                    {s.kind === "class" ? "C" : "ƒ"}
                  </span>
                  {s.name}
                </button>
              ))}
            </div>
          </div>
        )}
        {imports.length > 0 && (
          <div className="cp-row">
            <span className="eyebrow">Imports</span>
            <div className="chips">
              {imports.map((p) => (
                <Chip key={p} path={p} />
              ))}
            </div>
          </div>
        )}
        {importedBy.length > 0 && (
          <div className="cp-row">
            <span className="eyebrow">Used by</span>
            <div className="chips">
              {importedBy.map((p) => (
                <Chip key={p} path={p} />
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="cp-code mono" ref={codeRef}>
        {file.content.split("\n").map((text, i) => (
          <div
            key={i}
            data-line={i + 1}
            className={lit(i + 1) ? "cl hl" : "cl"}
          >
            <button className="cl-n" onClick={() => onOpen(file.path, i + 1)}>
              {i + 1}
            </button>
            <span className="cl-t">{text || " "}</span>
          </div>
        ))}
      </div>
    </aside>
  );
}
