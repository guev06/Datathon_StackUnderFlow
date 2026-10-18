const PASTELS = ['#c9d8f0', '#e2d4f0', '#f3d6dc', '#f6dccb', '#d3e5d3', '#f3ead0', '#cfe6ea', '#e9d6c8'];

export function groupColors(groups: string[]) {
  return Object.fromEntries(groups.map((g, i) => [g, PASTELS[i % PASTELS.length]]));
}
