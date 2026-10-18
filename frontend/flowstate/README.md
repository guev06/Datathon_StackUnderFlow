# FlowState — frontend

A minimal, Cursor-style landing page and an interactive **dataflow explorer** that turns a repository into a clickable dependency graph.


## Run

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # production build in dist/
```

## Adding your brand assets

| Asset | Where it goes |
| --- | --- |
| Logo | `public/brand/logo.png` (or change `brand.logo` in `src/config/brand.ts`) |
| Hero painting | `public/paintings/monet.webp` |
| CTA painting | `public/paintings/monet.webp` (same image; point `brand.paintings.section` elsewhere to use a second one) |

If a painting is missing, a soft CSS impressionist gradient is shown in their place. The paintings get a light off-white wash so text stays readable; you can tune that in `.hero-wash` (`src/components/Hero.css`) and `.cta-wash`.

Colours, fonts and radii are all tokens in `src/styles/tokens.css`.

## How the explorer works

`/explore?repo=owner/name` →

1. `src/lib/analyze.ts` reads the repo's file tree from the GitHub API, then fetches up to 150 JS/TS/Python source files from `raw.githubusercontent.com`.
2. `src/lib/parse.ts` pulls out imports (resolving relative paths, `index` files, `@/` aliases and Python packages) and top-level functions and classes.
3. `src/lib/layout.ts` lays the graph out left to right with dagre, and React Flow renders it.
4. Clicking a node updates the URL (`&file=…&line=…`) and opens the source panel. From there you can jump to symbols, imports, "used by" files, or **Open on GitHub** at the exact line. Every view has its own URL, so you can share or bookmark it.

With no `repo` (or if GitHub fails) it shows the bundled demo in `src/data/demo.ts`.

**Limits:** it only works with public repos, and unauthenticated GitHub API calls are capped at 60 per hour per IP (each analysis uses 2). For private repos or bigger codebases, move `analyzeGitHubRepo` behind your own backend. `RepoGraph` in `src/lib/types.ts` is the contract between the two.

## Structure

```
src/
  config/brand.ts          name, logo, painting paths
  styles/                  tokens + globals
  components/              landing page sections, preview windows, repo input
  components/explorer/     graph, custom node, sidebar, code panel
  lib/                     GitHub analyzer, import parser, layout, palette
  pages/                   Landing, Explorer
  data/demo.ts             offline sample repo
```
