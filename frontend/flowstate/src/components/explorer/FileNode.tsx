import { Handle, Position, type NodeProps, type Node } from '@xyflow/react';
import { memo, type CSSProperties } from 'react';

export type FileNodeData = {
  label: string;
  dir: string;
  color: string;
  symbols: number;
  state: 'idle' | 'selected' | 'related' | 'dimmed';
};

function FileNodeView({ data }: NodeProps<Node<FileNodeData>>) {
  return (
    <div className={`fnode fnode-${data.state}`} style={{ '--node-color': data.color } as CSSProperties}>
      <Handle type="target" position={Position.Left} />
      <span className="fnode-swatch" />
      <div className="fnode-text">
        <span className="fnode-label mono">{data.label}</span>
        <span className="fnode-dir">{data.dir || '/'}</span>
      </div>
      {data.symbols > 0 && <span className="fnode-count">{data.symbols}</span>}
      <Handle type="source" position={Position.Right} />
    </div>
  );
}

export default memo(FileNodeView);
