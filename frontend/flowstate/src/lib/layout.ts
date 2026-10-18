import dagre from '@dagrejs/dagre';
import type { RepoGraph } from './types';

export const NODE_W = 190;
export const NODE_H = 52;

export function layout(graph: RepoGraph) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: 'LR', nodesep: 22, ranksep: 90, marginx: 40, marginy: 40 });
  g.setDefaultEdgeLabel(() => ({}));
  graph.files.forEach((f) => g.setNode(f.id, { width: NODE_W, height: NODE_H }));
  graph.edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);
  return Object.fromEntries(
    graph.files.map((f) => {
      const n = g.node(f.id);
      return [f.id, { x: n.x - NODE_W / 2, y: n.y - NODE_H / 2 }];
    }),
  );
}
