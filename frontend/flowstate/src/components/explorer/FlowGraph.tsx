import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useReactFlow,
  ReactFlowProvider,
  type Edge as RFEdge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useEffect, useMemo } from 'react';
import { layout, NODE_H, NODE_W } from '../../lib/layout';
import type { RepoGraph } from '../../lib/types';
import FileNodeView, { type FileNodeData } from './FileNode';

const nodeTypes = { file: FileNodeView };

type Props = {
  graph: RepoGraph;
  colors: Record<string, string>;
  visible: Set<string>;
  selected: string | null;
  onSelect: (id: string | null) => void;
};

function Graph({ graph, colors, visible, selected, onSelect }: Props) {
  const positions = useMemo(() => layout(graph), [graph]);
  const { fitView, getNode, getZoom, setCenter } = useReactFlow();

  const related = useMemo(() => {
    const set = new Set<string>();
    if (!selected) return set;
    for (const e of graph.edges) {
      if (e.source === selected) set.add(e.target);
      if (e.target === selected) set.add(e.source);
    }
    return set;
  }, [graph, selected]);

  const nodes: Node<FileNodeData>[] = useMemo(
    () =>
      graph.files
        .filter((f) => visible.has(f.id))
        .map((f) => ({
          id: f.id,
          type: 'file',
          position: positions[f.id],
          width: NODE_W,
          height: NODE_H,
          data: {
            label: f.label,
            dir: f.path.slice(0, -f.label.length - 1),
            color: colors[f.group],
            symbols: f.symbols.length,
            state: !selected ? 'idle' : f.id === selected ? 'selected' : related.has(f.id) ? 'related' : 'dimmed',
          },
        })),
    [graph, positions, colors, visible, selected, related],
  );

  const edges: RFEdge[] = useMemo(
    () =>
      graph.edges
        .filter((e) => visible.has(e.source) && visible.has(e.target))
        .map((e) => {
          const active = selected && (e.source === selected || e.target === selected);
          return {
            id: e.id,
            source: e.source,
            target: e.target,
            type: 'smoothstep',
            animated: !!active,
            className: active ? 'edge-active' : selected ? 'edge-dimmed' : undefined,
          };
        }),
    [graph, visible, selected],
  );

  useEffect(() => {
    requestAnimationFrame(() => fitView({ padding: 0.15, duration: 400 }));
  }, [graph, fitView]);

  useEffect(() => {
    if (!selected) return;
    // wait for the code panel to open and the canvas to resize before centering
    const t = setTimeout(() => {
      const n = getNode(selected);
      if (n) setCenter(n.position.x + NODE_W / 2, n.position.y + NODE_H / 2, { zoom: Math.max(getZoom(), 0.9), duration: 500 });
    }, 120);
    return () => clearTimeout(t);
  }, [selected, getNode, getZoom, setCenter]);

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={nodeTypes}
      onNodeClick={(_, n) => onSelect(n.id)}
      onPaneClick={() => onSelect(null)}
      nodesConnectable={false}
      minZoom={0.15}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={22} size={1} color="#dcd7cc" />
      <Controls showInteractive={false} position="bottom-left" />
      <MiniMap
        pannable
        zoomable
        position="bottom-right"
        nodeColor={(n) => (n.data as FileNodeData).color}
        nodeStrokeColor="#b8b2a5"
        nodeStrokeWidth={3}
        nodeBorderRadius={8}
        bgColor="#fbfaf7"
        maskColor="rgba(247,245,240,.7)"
      />
    </ReactFlow>
  );
}

export default function FlowGraph(props: Props) {
  return (
    <ReactFlowProvider>
      <Graph {...props} />
    </ReactFlowProvider>
  );
}
