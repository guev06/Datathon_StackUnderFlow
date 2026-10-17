import dagre from '@dagrejs/dagre';
import {
  Background,
  Controls,
  MarkerType,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge as RFEdge,
  type Node,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useEffect, useMemo } from 'react';
import { ROLE_META } from '../../lib/roles';
import type { Analysis, Role } from '../../lib/types';
import StageNodeView, { STAGE_W, stageHeight, type StageNodeData } from './StageNode';

const nodeTypes = { stage: StageNodeView };

type Props = {
  analysis: Analysis;
  selected: string | null; // stage id
  activeSymbol: string | null;
  hiddenRoles: Set<Role>;
  showCalls: boolean;
  onSelect: (stageId: string | null) => void;
  onSymbol: (symbolId: string) => void;
};

function layoutStages(analysis: Analysis) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', nodesep: 40, ranksep: 110, marginx: 40, marginy: 40 });
  g.setDefaultEdgeLabel(() => ({}));
  const { stages, flows } = analysis.dataflow;
  stages.forEach((s) => g.setNode(s.id, { width: STAGE_W, height: stageHeight(s.refs.length) }));
  flows.filter((f) => f.kind === 'flow').forEach((f) => g.setEdge(f.source, f.target));
  dagre.layout(g);

  // Long flows are mostly chains, which dagre lays out as one very wide row. Wrap its columns (ranks) into
  // rows so the whole flow fits on screen, keeping dagre's vertical placement within each rank.
  const ranks = [...new Set(stages.map((s) => Math.round(g.node(s.id).x)))].sort((a, b) => a - b);
  const perRow = ranks.length > 4 ? Math.ceil(ranks.length / Math.ceil(ranks.length / 4)) : ranks.length;
  const rowOf = (s: (typeof stages)[number]) => Math.floor(ranks.indexOf(Math.round(g.node(s.id).x)) / perRow);
  const rowTop: number[] = [];
  const rowBottom: number[] = [];
  for (const s of stages) {
    const n = g.node(s.id);
    const r = rowOf(s);
    rowTop[r] = Math.min(rowTop[r] ?? Infinity, n.y - n.height / 2);
    rowBottom[r] = Math.max(rowBottom[r] ?? -Infinity, n.y + n.height / 2);
  }
  const rowY: number[] = [];
  rowTop.forEach((_, r) => (rowY[r] = r === 0 ? 0 : rowY[r - 1] + (rowBottom[r - 1] - rowTop[r - 1]) + ROW_GAP));
  return Object.fromEntries(
    stages.map((s) => {
      const n = g.node(s.id);
      const r = rowOf(s);
      const col = ranks.indexOf(Math.round(n.x)) % perRow;
      return [s.id, { x: col * (STAGE_W + COL_GAP), y: rowY[r] + (n.y - n.height / 2 - rowTop[r]), row: r }];
    }),
  );
}

const COL_GAP = 110;
const ROW_GAP = 90;

function Graph({ analysis, selected, activeSymbol, hiddenRoles, showCalls, onSelect, onSymbol }: Props) {
  const { stages, flows } = analysis.dataflow;
  const positions = useMemo(() => layoutStages(analysis), [analysis]);
  const symbolsById = useMemo(() => new Map(analysis.symbols.map((s) => [s.id, s])), [analysis]);
  const { fitView, getNode, setCenter, getZoom } = useReactFlow();

  const related = useMemo(() => {
    const set = new Set<string>();
    if (!selected) return set;
    for (const f of flows) {
      if (f.source === selected) set.add(f.target);
      if (f.target === selected) set.add(f.source);
    }
    return set;
  }, [flows, selected]);

  const nodes: Node<StageNodeData>[] = useMemo(
    () =>
      stages.map((stage, index) => ({
        id: stage.id,
        type: 'stage',
        position: { x: positions[stage.id].x, y: positions[stage.id].y },
        width: STAGE_W,
        height: stageHeight(stage.refs.length),
        data: {
          index,
          stage,
          symbols: stage.refs.map((r) => symbolsById.get(r)).filter((s) => !!s),
          activeSymbol,
          onSymbol,
          state: hiddenRoles.has(stage.kind)
            ? 'dimmed'
            : !selected
              ? 'idle'
              : stage.id === selected
                ? 'selected'
                : related.has(stage.id)
                  ? 'related'
                  : 'dimmed',
        },
      })),
    [stages, positions, symbolsById, activeSymbol, onSymbol, hiddenRoles, selected, related],
  );

  const edges: RFEdge[] = useMemo(
    () =>
      flows
        .filter((f) => f.kind === 'flow' || showCalls)
        .map((f, i) => {
          const active = !!selected && (f.source === selected || f.target === selected);
          const ink = ROLE_META[stages.find((s) => s.id === f.source)?.kind ?? 'transform'].ink;
          return {
            id: `${f.source}-${f.target}-${i}`,
            source: f.source,
            target: f.target,
            label: f.kind === 'flow' ? f.label || undefined : undefined,
            // Arrows that wrap to the next row read better as right-angled paths.
            type: f.kind === 'call' || positions[f.source]?.row !== positions[f.target]?.row ? 'smoothstep' : 'default',
            animated: f.kind === 'flow' && (active || !selected),
            className: [
              f.kind === 'call' ? 'edge-call' : 'edge-flow',
              active ? 'edge-active' : selected ? 'edge-dimmed' : '',
            ].join(' '),
            markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: active ? '#a98bc4' : '#bdb6a8' },
            labelBgPadding: [8, 4] as [number, number],
            labelBgBorderRadius: 999,
            labelStyle: { fill: active ? ink : '#6f6b62', fontSize: 11, fontWeight: 500 },
            labelBgStyle: { fill: '#fbfaf7', stroke: '#e6e2d9' },
          };
        }),
    [flows, stages, positions, selected, showCalls],
  );

  useEffect(() => {
    // Wait a frame for React Flow to measure the nodes, otherwise the fit uses stale bounds.
    const t = setTimeout(() => fitView({ padding: 0.14, duration: 400 }), 60);
    return () => clearTimeout(t);
  }, [analysis, fitView]);

  useEffect(() => {
    if (!selected) return;
    const t = setTimeout(() => {
      const n = getNode(selected);
      if (n?.width && n.height)
        setCenter(n.position.x + n.width / 2, n.position.y + n.height / 2, { zoom: Math.max(getZoom(), 0.85), duration: 500 });
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
      fitView
      fitViewOptions={{ padding: 0.14 }}
      nodesConnectable={false}
      minZoom={0.2}
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={22} size={1} color="#dcd7cc" />
      <Controls showInteractive={false} position="bottom-left" />
      <MiniMap
        pannable
        zoomable
        position="bottom-right"
        nodeColor={(n) => ROLE_META[(n.data as StageNodeData).stage.kind].color}
        nodeStrokeColor="#b8b2a5"
        nodeStrokeWidth={3}
        nodeBorderRadius={10}
        bgColor="#fbfaf7"
        maskColor="rgba(247,245,240,.7)"
      />
    </ReactFlow>
  );
}

export default function DataflowGraph(props: Props) {
  return (
    <ReactFlowProvider>
      <Graph {...props} />
    </ReactFlowProvider>
  );
}
