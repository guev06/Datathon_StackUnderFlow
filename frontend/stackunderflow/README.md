# Flowstate frontend

A React + Vite prototype for previewing a flowchart, browsing standard
flowchart symbols, and viewing a source script. The frontend uses local mock
data and does not require a backend or call an LLM.

## Run locally

```sh
npm install
npm run dev
```

Run `npm run lint` and `npm run build` to validate the frontend.

## Mock flowchart

The sample flow and standard symbol catalog are defined in
`src/data/mockFlowchart.js`. Load the included number-check sample with the
**Load sample** button, or use **Upload code** to preview a `.py` or `.txt`
file.

Uploaded source is read locally and can be viewed in the collapsible source
panel. There is no code parsing or execution: uploads currently preview the
static number-check flow. The included sample is
`public/samples/number_check.py`.

The flow model contains a title, description, read-only nodes, and SVG-path
connections. These data shapes can later be supplied by the model/API.
