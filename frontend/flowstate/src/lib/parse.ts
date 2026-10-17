import type { SymbolRef } from './types';

export const SOURCE_EXT = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs', '.py'];
const JS_EXT = ['.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs'];

export function languageOf(path: string) {
  if (path.endsWith('.py')) return 'python';
  if (/\.tsx?$/.test(path)) return 'typescript';
  return 'javascript';
}

export function extractImports(path: string, content: string): string[] {
  const specs: string[] = [];
  if (languageOf(path) === 'python') {
    for (const m of content.matchAll(/^\s*from\s+([.\w]+)\s+import\s+([\w*, ()]+)/gm)) {
      // `from . import a, b` refers to sibling modules a and b
      if (/^\.+$/.test(m[1])) {
        for (const name of m[2].replace(/[()]/g, '').split(',')) specs.push(m[1] + name.trim());
      } else {
        specs.push(m[1]);
      }
    }
    for (const m of content.matchAll(/^\s*import\s+([\w.]+)/gm)) specs.push(m[1]);
  } else {
    const re = /(?:import|export)\s[^'"]*?from\s*['"]([^'"]+)['"]|import\s*['"]([^'"]+)['"]|require\(\s*['"]([^'"]+)['"]\s*\)|import\(\s*['"]([^'"]+)['"]\s*\)/g;
    for (const m of content.matchAll(re)) specs.push(m[1] ?? m[2] ?? m[3] ?? m[4]);
  }
  return specs;
}

function normalize(parts: string[]) {
  const out: string[] = [];
  for (const p of parts) {
    if (p === '..') out.pop();
    else if (p !== '.' && p !== '') out.push(p);
  }
  return out.join('/');
}

function dirname(path: string) {
  const i = path.lastIndexOf('/');
  return i === -1 ? '' : path.slice(0, i);
}

/** Resolve an import specifier to a file in the repo, or null for external packages. */
export function resolveImport(from: string, spec: string, files: Set<string>): string | null {
  if (languageOf(from) === 'python') {
    let base: string;
    if (spec.startsWith('.')) {
      const dots = spec.match(/^\.+/)![0].length;
      let dir = dirname(from);
      for (let i = 1; i < dots; i++) dir = dirname(dir);
      base = normalize([dir, ...spec.slice(dots).split('.')]);
    } else {
      base = spec.replace(/\./g, '/');
    }
    for (const candidate of [`${base}.py`, `${base}/__init__.py`]) {
      if (files.has(candidate)) return candidate;
    }
    // absolute imports are often rooted in a src/ or package dir
    if (!spec.startsWith('.')) {
      for (const f of files) {
        if (f.endsWith(`/${base}.py`) || f.endsWith(`/${base}/__init__.py`)) return f;
      }
    }
    return null;
  }

  let base: string;
  if (spec.startsWith('.')) base = normalize([...dirname(from).split('/'), ...spec.split('/')]);
  else if (spec.startsWith('@/') || spec.startsWith('~/')) base = normalize(['src', ...spec.slice(2).split('/')]);
  else if (spec.startsWith('/')) base = normalize(spec.split('/'));
  else return null;

  if (files.has(base)) return base;
  const stripped = base.replace(/\.(js|jsx|mjs|cjs)$/, ''); // TS ESM imports often use .js
  for (const ext of JS_EXT) {
    if (files.has(stripped + ext)) return stripped + ext;
    if (files.has(`${stripped}/index${ext}`)) return `${stripped}/index${ext}`;
  }
  return null;
}

export function extractSymbols(path: string, content: string): SymbolRef[] {
  const lines = content.split('\n');
  const out: SymbolRef[] = [];
  const py = languageOf(path) === 'python';
  lines.forEach((text, i) => {
    let m: RegExpMatchArray | null;
    if (py) {
      if ((m = text.match(/^(?:async\s+)?def\s+(\w+)/))) out.push({ name: m[1], kind: 'function', line: i + 1 });
      else if ((m = text.match(/^class\s+(\w+)/))) out.push({ name: m[1], kind: 'class', line: i + 1 });
    } else {
      if ((m = text.match(/^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(\w+)/)))
        out.push({ name: m[1], kind: 'function', line: i + 1 });
      else if ((m = text.match(/^\s*(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)/)))
        out.push({ name: m[1], kind: 'class', line: i + 1 });
      else if ((m = text.match(/^(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?(?:\([^)]*\)|\w+)\s*=>/)))
        out.push({ name: m[1], kind: 'const', line: i + 1 });
    }
  });
  return out;
}
