import type { CodeSymbol, Role } from './types';

export const ROLE_META: Record<Role, { label: string; color: string; ink: string }> = {
  entry: { label: 'Entry', color: '#e2d4f0', ink: '#7a5f9a' },
  input: { label: 'Input', color: '#c9d8f0', ink: '#4f6f9f' },
  transform: { label: 'Transform', color: '#f3ead0', ink: '#97803f' },
  storage: { label: 'Storage', color: '#d3e5d3', ink: '#4f7f55' },
  output: { label: 'Output', color: '#f3d6dc', ink: '#a35a6b' },
};

export const ROLE_ORDER: Role[] = ['entry', 'input', 'transform', 'storage', 'output'];

export const KIND_ICON: Record<CodeSymbol['kind'], string> = { function: 'ƒ', method: 'ƒ', class: 'C', module: '▸' };

/** Top-level script code has no name of its own, so show the file it lives in. */
export const displayName = (s: CodeSymbol) => (s.kind === 'module' ? `${s.file.split('/').pop()} (script)` : s.name);
