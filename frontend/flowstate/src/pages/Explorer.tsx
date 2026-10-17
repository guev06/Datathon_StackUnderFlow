import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import Logo from '../components/Logo';
import RepoInput from '../components/RepoInput';
import CodePanel from '../components/explorer/CodePanel';
import DataflowGraph from '../components/explorer/DataflowGraph';
import DataflowSidebar from '../components/explorer/DataflowSidebar';
import FlowGraph from '../components/explorer/FlowGraph';
import ReportView from '../components/explorer/ReportView';
import Sidebar from '../components/explorer/Sidebar';
import StagePanel from '../components/explorer/StagePanel';
import { demoGraph } from '../data/demo';
import { analyzeGitHubRepo, buildGraph, parseRepoInput } from '../lib/analyze';
import { analyzeWithBackend, BackendUnavailable, type Progress } from '../lib/api';
import { groupColors } from '../lib/palette';
import type { Analysis, RepoGraph, Role } from '../lib/types';
import './Explorer.css';

type View = 'flow' | 'files' | 'report';

function toGraph(a: Analysis): RepoGraph {
  return buildGraph(
    { owner: a.owner, repo: a.repo, branch: a.branch, source: 'backend', truncated: a.truncated },
    a.files.map(({ path, content }) => ({ path, content })),
  );
}

export default function Explorer() {
  const [params, setParams] = useSearchParams();
  const repoParam = params.get('repo') ?? '';
  const selected = params.get('file');
  const line = params.get('line') ? Number(params.get('line')) : null;
  const end = params.get('end') ? Number(params.get('end')) : null;
  const stageId = params.get('stage');
  const symbolId = params.get('sym');

  const [graph, setGraph] = useState<RepoGraph | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [hiddenRoles, setHiddenRoles] = useState<Set<Role>>(new Set());
  const [showCalls, setShowCalls] = useState(true);
  const [query, setQuery] = useState('');
  const [playing, setPlaying] = useState(false);
  const [refresh, setRefresh] = useState(0);

  const view: View = (params.get('view') as View) ?? (analysis ? 'flow' : 'files');

  useEffect(() => {
    let cancelled = false;
    setError('');
    setHidden(new Set());
    setAnalysis(null);
    setProgress(null);
    setPlaying(false);
    const target = parseRepoInput(repoParam);
    if (!target) {
      if (repoParam) setError('Enter a repository as owner/repo or a GitHub URL.');
      setGraph(demoGraph);
      return;
    }
    setGraph(null);
    analyzeWithBackend(`${target.owner}/${target.repo}`, (p) => !cancelled && setProgress(p), () => cancelled, refresh > 0)
      .then((a) => {
        if (cancelled) return;
        setAnalysis(a);
        setGraph(toGraph(a));
      })
      .catch(async (e: Error) => {
        if (cancelled || e.message === 'cancelled') return;
        if (!(e instanceof BackendUnavailable)) {
          setError(`${e.message} Showing the demo instead.`);
          setGraph(demoGraph);
          return;
        }
        // Without the backend there is no AI dataflow, but the client-side import graph still works.
        setError('AI backend is offline (run backend/start.sh). Showing the import graph only.');
        try {
          const g = await analyzeGitHubRepo(target.owner, target.repo, (m) => !cancelled && setStatus(m));
          if (!cancelled) setGraph(g);
        } catch (err) {
          if (!cancelled) {
            setError(`${(err as Error).message} Showing the demo instead.`);
            setGraph(demoGraph);
          }
        }
      });
    return () => {
      cancelled = true;
    };
  }, [repoParam, refresh]);

  const colors = useMemo(
    () => (graph ? groupColors([...new Set(graph.files.map((f) => f.group))].sort()) : {}),
    [graph],
  );

  const visible = useMemo(() => {
    const q = query.toLowerCase();
    return new Set(
      (graph?.files ?? []).filter((f) => !hidden.has(f.group) && f.path.toLowerCase().includes(q)).map((f) => f.id),
    );
  }, [graph, hidden, query]);

  const update = useCallback(
    (changes: Record<string, string | number | null | undefined>) => {
      setParams((prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(changes)) {
          if (v === null || v === undefined || v === '') next.delete(k);
          else next.set(k, String(v));
        }
        return next;
      });
    },
    [setParams],
  );

  function open(path: string | null, ln?: number, endLn?: number) {
    update({ file: path, line: ln ?? null, end: endLn ?? null });
  }
  const selectStage = useCallback(
    (id: string | null) => update({ stage: id, sym: null, file: null, line: null, end: null }),
    [update],
  );
  const selectSymbol = useCallback(
    (id: string) => {
      const owner = analysis?.dataflow.stages.find((s) => s.refs.includes(id));
      update({ sym: id, stage: owner?.id ?? null, file: null, line: null, end: null });
    },
    [analysis, update],
  );

  const stages = analysis?.dataflow.stages ?? [];
  const stageIndex = stages.findIndex((s) => s.id === stageId);

  // Step-through playback of the dataflow.
  useEffect(() => {
    if (!playing || !stages.length) return;
    if (stageIndex === -1) {
      selectStage(stages[0].id);
      return;
    }
    const t = setTimeout(() => {
      if (stageIndex >= stages.length - 1) setPlaying(false);
      else selectStage(stages[stageIndex + 1].id);
    }, 2600);
    return () => clearTimeout(t);
  }, [playing, stageIndex, stages, selectStage]);

  // ← / → walk the steps, Esc closes the panel.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (view !== 'flow' || !stages.length || (e.target as HTMLElement).closest('input, textarea')) return;
      if (e.key === 'ArrowRight') selectStage(stages[Math.min(stageIndex + 1, stages.length - 1)].id);
      else if (e.key === 'ArrowLeft') selectStage(stages[Math.max(stageIndex - 1, 0)].id);
      else if (e.key === 'Escape') selectStage(null);
      else return;
      e.preventDefault();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [view, stages, stageIndex, selectStage]);

  function toggleGroup(g: string) {
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(g) ? next.delete(g) : next.add(g);
      return next;
    });
  }
  function toggleRole(r: Role) {
    setHiddenRoles((prev) => {
      const next = new Set(prev);
      next.has(r) ? next.delete(r) : next.add(r);
      return next;
    });
  }

  const file = graph?.files.find((f) => f.id === selected) ?? null;
  const showStagePanel = !file && !!analysis && (!!stageId || !!symbolId);
  const panelOpen = !!file || showStagePanel;

  const panel = file ? (
    <CodePanel graph={graph!} file={file} line={line} end={end} colors={colors} onOpen={open} onClose={() => open(null)} />
  ) : showStagePanel ? (
    <StagePanel
      graph={graph!}
      analysis={analysis!}
      stageId={stageId}
      symbolId={symbolId}
      onStage={selectStage}
      onSymbol={selectSymbol}
      onOpenFile={(p, l, e) => open(p, l, e)}
      onClose={() => update({ stage: null, sym: null })}
    />
  ) : null;

  const tabs: [View, string][] = [
    ['flow', 'Dataflow'],
    ['files', 'Files'],
    ['report', 'AI report'],
  ];

  return (
    <div className="explorer">
      <header className="ex-top">
        <Logo />
        <RepoInput initial={repoParam} compact key={repoParam} />
        {analysis && (
          <nav className="ex-tabs" aria-label="View">
            {tabs.map(([v, label]) => (
              <button key={v} className={view === v ? 'on' : ''} onClick={() => update({ view: v })}>
                {label}
              </button>
            ))}
          </nav>
        )}
        <div className="ex-hint">
          {view === 'flow' && analysis ? 'Click a step or function to see its code · ← → walk the flow' : 'Click a node to open its source'}
        </div>
      </header>
      {error && <div className="ex-error">{error}</div>}

      {!graph ? (
        <div className="ex-loading">
          <div className="loader" />
          {progress ? (
            <ol className="ex-steps">
              {progress.steps.map((s, me) => {
                const idx = progress.steps.findIndex((x) => x.id === progress.step);
                const state = idx === -1 ? 'todo' : me < idx ? 'done' : me === idx ? 'now' : 'todo';
                return (
                  <li key={s.id} className={`ex-step ${state}`}>
                    <span className="ex-step-dot">{state === 'done' ? '✓' : ''}</span>
                    {s.label}
                  </li>
                );
              })}
            </ol>
          ) : (
            <p className="mono">{status || 'Checking repository…'}</p>
          )}
          {progress && <p className="ex-loading-note">A new repo takes about a minute. Results are cached per commit.</p>}
        </div>
      ) : view === 'report' && analysis ? (
        <div className={`ex-body ex-body-report${panelOpen ? ' with-panel' : ''}`}>
          <ReportView analysis={analysis} onSymbol={selectSymbol} onFile={(p) => open(p)} />
          {panel}
        </div>
      ) : view === 'flow' && analysis ? (
        <div className={`ex-body${panelOpen ? ' with-panel' : ''}`}>
          <DataflowSidebar
            analysis={analysis}
            selected={stageId}
            hiddenRoles={hiddenRoles}
            showCalls={showCalls}
            onToggleRole={toggleRole}
            onToggleCalls={() => setShowCalls((v) => !v)}
            onSelect={selectStage}
            onSymbol={selectSymbol}
          />
          <div className="ex-canvas">
            <div className="flow-toolbar">
              <button className="btn icon" onClick={() => selectStage(stages[Math.max(stageIndex - 1, 0)].id)} aria-label="Previous step">
                ←
              </button>
              <button className="btn btn-primary" onClick={() => setPlaying((p) => !p)}>
                {playing ? '❚❚ Pause' : '▶ Play flow'}
              </button>
              <button
                className="btn icon"
                onClick={() => selectStage(stages[Math.min(stageIndex + 1, stages.length - 1)].id)}
                aria-label="Next step"
              >
                →
              </button>
              <span className="flow-toolbar-step mono">
                {stageIndex >= 0 ? `${stageIndex + 1} / ${stages.length}` : `${stages.length} steps`}
              </span>
              <button className="btn btn-ghost" onClick={() => setRefresh((n) => n + 1)} title="Run the models again">
                Re-analyse
              </button>
            </div>
            <DataflowGraph
              analysis={analysis}
              selected={stageId}
              activeSymbol={symbolId}
              hiddenRoles={hiddenRoles}
              showCalls={showCalls}
              onSelect={selectStage}
              onSymbol={selectSymbol}
            />
          </div>
          {panel}
        </div>
      ) : (
        <div className={`ex-body${panelOpen ? ' with-panel' : ''}`}>
          <Sidebar
            graph={graph}
            colors={colors}
            hidden={hidden}
            query={query}
            selected={selected}
            onQuery={setQuery}
            onToggleGroup={toggleGroup}
            onSelect={(id) => open(id)}
          />
          <div className="ex-canvas">
            <FlowGraph graph={graph} colors={colors} visible={visible} selected={selected} onSelect={(id) => open(id)} />
          </div>
          {panel}
        </div>
      )}
    </div>
  );
}
