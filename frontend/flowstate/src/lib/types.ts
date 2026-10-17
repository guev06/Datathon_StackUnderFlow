export type SymbolRef = { name: string; kind: 'function' | 'class' | 'const'; line: number };

export type FileNode = {
  id: string; // repo-relative path
  path: string;
  label: string; // file name
  group: string; // top-level directory
  language: string;
  lines: number;
  symbols: SymbolRef[];
  content: string;
};

export type Edge = { id: string; source: string; target: string };

export type RepoGraph = {
  owner: string;
  repo: string;
  branch: string;
  source: 'github' | 'demo' | 'backend';
  files: FileNode[];
  edges: Edge[];
  truncated: boolean;
};

export type Role = 'entry' | 'input' | 'transform' | 'storage' | 'output';

export type CodeSymbol = {
  id: string; // `${file}::${name}`
  file: string;
  name: string;
  kind: 'function' | 'method' | 'class' | 'module';
  line: number;
  end_line: number;
  signature: string;
  doc: string;
};

export type Stage = { id: string; title: string; summary: string; kind: Role; refs: string[]; files: string[] };

export type Flow = { source: string; target: string; label: string; kind: 'flow' | 'call'; calls: number };

/** Response of the FlowState backend (backend/repo_dataflow_ai/server.py). */
export type Analysis = {
  owner: string;
  repo: string;
  branch: string;
  sha: string;
  truncated: boolean;
  engine: string;
  role_model: string;
  report_md: string;
  files: { path: string; content: string; has_main: boolean }[];
  symbols: CodeSymbol[];
  calls: { source: string; target: string }[];
  dataflow: {
    stages: Stage[];
    flows: Flow[];
    source: 'model' | 'heuristic';
    roles: Record<string, { role: Role; confidence: number }>;
  };
  timings: Record<string, number>;
};

export type JobStep = { id: string; label: string };
