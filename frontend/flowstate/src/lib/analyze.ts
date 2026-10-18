import { extractImports, extractSymbols, languageOf, resolveImport, SOURCE_EXT } from './parse';
import type { Edge, FileNode, RepoGraph } from './types';

const MAX_FILES = 150;
const IGNORE = /(^|\/)(node_modules|dist|build|out|vendor|coverage|\.next|\.git|__pycache__|venv|\.venv)\//;
const TEST = /(\.test\.|\.spec\.|(^|\/)tests?\/|__tests__)/;

export function parseRepoInput(input: string): { owner: string; repo: string } | null {
  const cleaned = input.trim().replace(/^https?:\/\//, '').replace(/^github\.com\//, '').replace(/\.git$/, '');
  const [owner, repo] = cleaned.split('/');
  if (!owner || !repo) return null;
  return { owner, repo };
}

export function buildGraph(
  meta: Pick<RepoGraph, 'owner' | 'repo' | 'branch' | 'source' | 'truncated'>,
  sources: { path: string; content: string }[],
): RepoGraph {
  const paths = new Set(sources.map((s) => s.path));
  const files: FileNode[] = sources.map(({ path, content }) => {
    const parts = path.split('/');
    const rel = parts[0] === 'src' ? parts.slice(1) : parts;
    return {
      id: path,
      path,
      label: parts[parts.length - 1],
      group: rel.length > 1 ? rel[0] : '(root)',
      language: languageOf(path),
      lines: content.split('\n').length,
      symbols: extractSymbols(path, content),
      content,
    };
  });

  const seen = new Set<string>();
  const edges: Edge[] = [];
  for (const { path, content } of sources) {
    for (const spec of extractImports(path, content)) {
      const target = resolveImport(path, spec, paths);
      const id = `${path}->${target}`;
      if (target && target !== path && !seen.has(id)) {
        seen.add(id);
        edges.push({ id, source: path, target });
      }
    }
  }
  return { ...meta, files, edges };
}

async function gh<T>(url: string): Promise<T> {
  const res = await fetch(url, { headers: { Accept: 'application/vnd.github+json' } });
  if (res.status === 403) throw new Error('GitHub rate limit reached. Try again in a few minutes.');
  if (res.status === 404) throw new Error('Repository not found (it must be public).');
  if (!res.ok) throw new Error(`GitHub responded with ${res.status}.`);
  return res.json();
}

async function mapLimit<T, R>(items: T[], limit: number, fn: (t: T) => Promise<R>): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let i = 0;
  await Promise.all(
    Array.from({ length: Math.min(limit, items.length) }, async () => {
      while (i < items.length) {
        const idx = i++;
        out[idx] = await fn(items[idx]);
      }
    }),
  );
  return out;
}

export async function analyzeGitHubRepo(
  owner: string,
  repo: string,
  onProgress?: (msg: string) => void,
): Promise<RepoGraph> {
  onProgress?.('Fetching repository…');
  const info = await gh<{ default_branch: string }>(`https://api.github.com/repos/${owner}/${repo}`);
  const branch = info.default_branch;

  onProgress?.('Reading file tree…');
  const tree = await gh<{ tree: { path: string; type: string; size?: number }[] }>(
    `https://api.github.com/repos/${owner}/${repo}/git/trees/${branch}?recursive=1`,
  );
  const candidates = tree.tree
    .filter((t) => t.type === 'blob' && SOURCE_EXT.some((e) => t.path.endsWith(e)))
    .filter((t) => !IGNORE.test(t.path) && !TEST.test(t.path) && !t.path.endsWith('.d.ts') && (t.size ?? 0) < 200_000)
    .sort((a, b) => a.path.split('/').length - b.path.split('/').length);
  if (candidates.length === 0) throw new Error('No JavaScript, TypeScript or Python source files found.');

  const picked = candidates.slice(0, MAX_FILES);
  let done = 0;
  const sources = await mapLimit(picked, 8, async ({ path }) => {
    const res = await fetch(`https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${path}`);
    onProgress?.(`Parsing files… ${++done}/${picked.length}`);
    return { path, content: res.ok ? await res.text() : '' };
  });

  return buildGraph({ owner, repo, branch, source: 'github', truncated: candidates.length > MAX_FILES }, sources);
}

export function githubUrl(g: RepoGraph, path: string, line?: number) {
  return `https://github.com/${g.owner}/${g.repo}/blob/${g.branch}/${path}${line ? `#L${line}` : ''}`;
}
