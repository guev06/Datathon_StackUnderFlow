import { Handle, Position, type Node, type NodeProps } from '@xyflow/react';
import { memo, type CSSProperties } from 'react';
import { displayName, KIND_ICON, ROLE_META } from '../../lib/roles';
import type { CodeSymbol, Stage } from '../../lib/types';

export type StageNodeData = {
  index: number;
  stage: Stage;
  symbols: CodeSymbol[];
  activeSymbol: string | null;
  state: 'idle' | 'selected' | 'related' | 'dimmed';
  onSymbol: (id: string) => void;
};

export const STAGE_W = 280;
export const stageHeight = (refs: number) => 96 + 28 * Math.min(refs, 6);

function StageNodeView({ data }: NodeProps<Node<StageNodeData>>) {
  const { stage, symbols, index, state, activeSymbol, onSymbol } = data;
  const meta = ROLE_META[stage.kind];
  return (
    <div
      className={`snode snode-${state}`}
      style={{ '--node-color': meta.color, '--node-ink': meta.ink, width: STAGE_W } as CSSProperties}
    >
      <Handle type="target" position={Position.Left} />
      <header className="snode-head">
        <span className="snode-n mono">{String(index + 1).padStart(2, '0')}</span>
        <span className="snode-kind">{meta.label}</span>
      </header>
      <div className="snode-title">{stage.title}</div>
      <div className="snode-summary" title={stage.summary}>{stage.summary}</div>
      <ul className="snode-refs">
        {symbols.slice(0, 6).map((s) => (
          <li key={s.id}>
            <button
              className={`snode-ref mono${activeSymbol === s.id ? ' on' : ''}`}
              title={`${s.signature}\n${s.file}:${s.line}`}
              onClick={(e) => {
                e.stopPropagation();
                onSymbol(s.id);
              }}
            >
              <span className="snode-ref-kind">{KIND_ICON[s.kind]}</span>
              <span className="snode-ref-name">{displayName(s)}</span>
              <span className="snode-ref-loc">{s.file.split('/').pop()}:{s.line}</span>
            </button>
          </li>
        ))}
      </ul>
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export default memo(StageNodeView);
