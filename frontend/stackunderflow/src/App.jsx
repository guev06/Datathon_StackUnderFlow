import { useRef, useState } from "react";
import { FlowchartSymbol } from "./components/FlowchartSymbol.jsx";
import {
  createNumberCheckFlowchart,
  flowchartSymbols,
  initialFlowchart,
} from "./data/mockFlowchart.js";
import "./App.css";
import flowStateLogo from "../src/assets/flowState_logo-removebg-preview.png";
function Icon({ name, size = 18 }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.7,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": true,
  };

  if (name === "grid")
    return (
      <svg {...common}>
        <rect x="3.5" y="3.5" width="7" height="7" rx="1.5" />
        <rect x="13.5" y="3.5" width="7" height="7" rx="1.5" />
        <rect x="3.5" y="13.5" width="7" height="7" rx="1.5" />
        <rect x="13.5" y="13.5" width="7" height="7" rx="1.5" />
      </svg>
    );
  if (name === "chevron")
    return (
      <svg {...common}>
        <path d="m9 18 6-6-6-6" />
      </svg>
    );
  if (name === "moon")
    return (
      <svg {...common}>
        <path d="M20.8 14.1A8.5 8.5 0 0 1 9.9 3.2 8.5 8.5 0 1 0 20.8 14.1Z" />
      </svg>
    );
  if (name === "sun")
    return (
      <svg {...common}>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
      </svg>
    );
  if (name === "upload")
    return (
      <svg {...common}>
        <path d="M12 16V4m-4 4 4-4 4 4" />
        <path d="M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5" />
      </svg>
    );
  if (name === "panel-left")
    return (
      <svg {...common}>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M9 4v16m5-11 3 3-3 3" />
      </svg>
    );
  if (name === "panel-right")
    return (
      <svg {...common}>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M15 4v16m-5-11-3 3 3 3" />
      </svg>
    );
  return (
    <svg {...common}>
      <path d="m5 12 4 4L19 6" />
    </svg>
  );
}

function App() {
  const [flowchart, setFlowchart] = useState(initialFlowchart);
  const [workspaceFiles, setWorkspaceFiles] = useState([
    {
      id: "number_check.py",
      name: "number_check.py",
      source: "",
      isSample: true,
    },
  ]);
  const [activeView, setActiveView] = useState("chart");
  const [isDark, setIsDark] = useState(
    () => localStorage.getItem("flowstate-theme") === "dark",
  );
  const [sourceOpen, setSourceOpen] = useState(false);
  const [symbolsOpen, setSymbolsOpen] = useState(true);
  const [uploadStatus, setUploadStatus] = useState("");
  const [sourceCode, setSourceCode] = useState("");
  const [isCanvasScrolled, setIsCanvasScrolled] = useState(false);
  const fileInputRef = useRef(null);

  function openWorkspace() {
    setActiveView("workspace");
    setUploadStatus("");
  }

  function toggleTheme() {
    setIsDark((current) => {
      const next = !current;
      localStorage.setItem("flowstate-theme", next ? "dark" : "light");
      return next;
    });
  }

  function showMockPreview(fileName, source, status) {
    const id = fileName.toLowerCase();
    setWorkspaceFiles((files) => {
      const existingFile = files.find((file) => file.id === id);
      const nextFile = {
        id,
        name: fileName,
        source,
        isSample: existingFile?.isSample ?? false,
      };
      return existingFile
        ? files.map((file) => (file.id === id ? nextFile : file))
        : [...files, nextFile];
    });
    setFlowchart(createNumberCheckFlowchart(fileName));
    setSourceCode(source);
    setUploadStatus(status);
    setActiveView("chart");
  }

  async function openWorkspaceFile(file) {
    try {
      let source = file.source;
      if (file.isSample && !source) {
        const response = await fetch("/samples/number_check.py");
        if (!response.ok) {
          throw new Error(`The sample returned HTTP ${response.status}.`);
        }
        source = await response.text();
      }
      showMockPreview(
        file.name,
        source,
        `Opened ${file.name}. The chart is a static preview; code is not analyzed or executed.`,
      );
      setSourceOpen(true);
    } catch (error) {
      setUploadStatus(`Could not open ${file.name}: ${error.message}`);
    }
  }

  async function loadSourceFile(file) {
    const lowerName = file.name.toLowerCase();
    if (!lowerName.endsWith(".py") && !lowerName.endsWith(".txt")) {
      setUploadStatus("Choose a .py or .txt source file.");
      return;
    }
    if (file.size > 1024 * 1024) {
      setUploadStatus("This demo accepts files up to 1 MB.");
      return;
    }

    try {
      const source = await file.text();
      if (!source.trim()) {
        setUploadStatus(
          "The selected file is empty. Choose a source file with code.",
        );
        return;
      }
      showMockPreview(
        file.name,
        source,
        `Loaded ${file.name}. The chart is a static sample; uploaded code is not analyzed yet.`,
      );
      setSourceOpen(true);
    } catch (error) {
      setUploadStatus(`Could not read ${file.name}: ${error.message}`);
    }
  }

  async function loadSample() {
    try {
      const response = await fetch("/samples/number_check.py");
      if (!response.ok) {
        throw new Error(`The sample returned HTTP ${response.status}.`);
      }
      const source = await response.text();
      showMockPreview(
        "number_check.py",
        source,
        "Number check sample loaded. The flowchart is a static preview.",
      );
    } catch (error) {
      setUploadStatus(`Could not load the sample: ${error.message}`);
    }
  }

  function moveDemoWave(event) {
    if (!flowchart.isMockOutput || event.pointerType === "touch") return;

    const bounds = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - bounds.left) / bounds.width) * 100;
    const y = ((event.clientY - bounds.top) / bounds.height) * 100;
    event.currentTarget.style.setProperty("--wave-x", `${x}%`);
    event.currentTarget.style.setProperty("--wave-y", `${y}%`);
  }

  function resetDemoWave(event) {
    event.currentTarget.style.setProperty("--wave-x", "50%");
    event.currentTarget.style.setProperty("--wave-y", "50%");
  }

  const canvasHeight = Math.max(
    600,
    ...flowchart.nodes.map(
      (node) => node.position.y + (node.type === "decision" ? 140 : 110),
    ),
  );

  return (
    <main className="app-shell" data-theme={isDark ? "dark" : "light"}>
      <header className="topbar">
        <button
          className="brand"
          onClick={openWorkspace}
          aria-label="Open Flowstate workspace"
          type="button"
        >
          <span>
            <img
              src={flowStateLogo}
              alt="FlowState logo"
              style={{ width: "20px", height: "auto", marginTop: "7px" }}
            />
          </span>{" "}
          <span>
            flow<span className="brand-accent">state</span>
          </span>
        </button>
        <div className="topbar-divider" />
        <nav className="breadcrumbs" aria-label="Breadcrumb">
          <button
            className={activeView === "workspace" ? "is-current" : ""}
            onClick={openWorkspace}
            type="button"
          >
            My workspace
          </button>
          {activeView === "chart" && (
            <>
              <Icon name="chevron" size={14} />
              <span>{flowchart.sourceFile || flowchart.title}</span>
            </>
          )}
        </nav>
        <div className="topbar-actions">
          {activeView === "chart" && flowchart.sourceFile && (
            <span className="source-file-name">{flowchart.sourceFile}</span>
          )}
          <input
            accept=".py,.txt,text/plain"
            className="file-input"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void loadSourceFile(file);
              event.target.value = "";
            }}
            ref={fileInputRef}
            type="file"
          />
          <button
            aria-label={`Switch to ${isDark ? "light" : "dark"} mode`}
            className="theme-toggle"
            onClick={toggleTheme}
            type="button"
          >
            <Icon name={isDark ? "sun" : "moon"} size={17} />
            <span>{isDark ? "Light mode" : "Dark mode"}</span>
          </button>
        </div>
      </header>

      <section
        className={`workspace${activeView === "workspace" ? " home-view" : ""}${sourceOpen ? " source-open" : ""}${symbolsOpen ? "" : " symbols-collapsed"}`}
        id="workspace"
        aria-label="Flowchart workspace"
      >
        {activeView === "workspace" ? (
          <section className="workspace-home" aria-labelledby="workspace-title">
            <div className="workspace-home-heading">
              <div>
                <span className="eyebrow">YOUR FILES</span>
                <h1 id="workspace-title">My workspace</h1>
                <p>Open a file to view its source and flowchart preview.</p>
              </div>
              <button
                className="upload-button"
                onClick={() => fileInputRef.current?.click()}
                type="button"
              >
                <Icon name="upload" size={16} />
                <span>Add file</span>
              </button>
            </div>
            {uploadStatus && (
              <p className="workspace-status" role="status">
                {uploadStatus}
              </p>
            )}
            <div className="workspace-file-list" aria-label="Workspace files">
              {workspaceFiles.map((file) => (
                <button
                  className="workspace-file"
                  key={file.id}
                  onClick={() => void openWorkspaceFile(file)}
                  type="button"
                >
                  <span className="workspace-file-icon" aria-hidden="true">
                    {file.name.split(".").pop()?.toUpperCase() || "FILE"}
                  </span>
                  <span className="workspace-file-details">
                    <strong>{file.name}</strong>
                    <span>{file.isSample ? "Sample file" : "Uploaded file"} · Flowchart preview available</span>
                  </span>
                  <Icon name="chevron" size={17} />
                </button>
              ))}
            </div>
          </section>
        ) : (
          <>
        <aside
          className={`source-sidebar${sourceOpen ? "" : " is-collapsed"}`}
          aria-label="Source code"
        >
          
          {sourceOpen && (
            <div className="sidebar-content" id="source-content">
              <div className="sidebar-heading">
                <span className="eyebrow">SOURCE</span>
                <h2>{flowchart.sourceFile || "Number check sample"}</h2>
                <p>
                  {sourceCode
                    ? "Read-only preview of the loaded Python file."
                    : "Load the sample or upload a Python file to view its source."}
                </p>
              </div>
              {sourceCode ? (
                <pre className="source-code">
                  <code>{sourceCode}</code>
                </pre>
              ) : (
                <button
                  className="source-sample-button"
                  onClick={() => void loadSample()}
                  type="button"
                >
                  Load sample
                </button>
              )}
            </div>
          )}
        </aside>

        <section className="editor" aria-label="Flowchart preview">
          <header
            className={`editor-heading${flowchart.isMockOutput ? " is-demo" : ""}${isCanvasScrolled ? " is-compact" : ""}`}
            onPointerLeave={resetDemoWave}
            onPointerMove={moveDemoWave}
          >
            <div className="editor-title">
              <span className="eyebrow">
                {flowchart.isMockOutput ? "DEMO PREVIEW" : "FLOWCHART"}
              </span>
              <h1>{flowchart.title}</h1>
              <p>{flowchart.description}</p>
            </div>
            <div className="editor-actions">
              <button
                className="upload-button"
                onClick={() => fileInputRef.current?.click()}
                type="button"
              >
                <Icon name="upload" size={16} />
                <span>Upload code</span>
              </button>
              <a
                className="sample-download"
                download
                href="/samples/number_check.py"
              >
                Get sample
              </a>
            </div>
          </header>

          <div
            aria-live="polite"
            className={`upload-feedback${uploadStatus ? " has-message" : ""}`}
            role="status"
          >
            {uploadStatus}
          </div>

          <div className="canvas-toolbar">
            <span>
              <span className="legend-line" /> FLOW{" "}
              <span className="legend-separator">·</span>{" "}
              {flowchart.nodes.length} STEPS
            </span>
            <button
              className="sample-button"
              onClick={() => void loadSample()}
              type="button"
            >
              Load sample
            </button>
          </div>

          <div
            className="canvas-scroll"
            onScroll={(event) =>
              setIsCanvasScrolled(event.currentTarget.scrollTop > 16)
            }
          >
            <div
              className="flow-canvas"
              style={{ height: `${canvasHeight}px` }}
            >
              <svg
                aria-label={`${flowchart.title} connections`}
                className="flow-connectors"
                height={canvasHeight}
                preserveAspectRatio="none"
                viewBox={`0 0 900 ${canvasHeight}`}
                width="900"
                role="img"
              >
                <defs>
                  <marker
                    id="arrowhead"
                    markerWidth="8"
                    markerHeight="8"
                    refX="6"
                    refY="4"
                    orient="auto"
                  >
                    <path
                      d="M1 1 6 4 1 7"
                      fill="none"
                      stroke="#9299a9"
                      strokeWidth="1.4"
                    />
                  </marker>
                </defs>
                <g className="connection-paths">
                  {flowchart.connections.map((connection, index) => {
                    return (
                      <path
                        d={connection.path}
                        key={`connection-${index}`}
                        markerEnd="url(#arrowhead)"
                      />
                    );
                  })}
                </g>
                <g className="branch-labels">
                  {flowchart.connections
                    .filter((connection) => connection.label)
                    .map((connection, index) => {
                      const { x, y } = connection.label;
                      const text = connection.label.text;
                      const width = Math.max(34, text.length * 7 + 12);
                      return (
                        <g key={`branch-${index}`}>
                          <rect
                            x={x - width / 2}
                            y={y - 11}
                            width={width}
                            height="22"
                            rx="11"
                          />
                          <text x={x} y={y + 3}>
                            {text.toUpperCase()}
                          </text>
                        </g>
                      );
                    })}
                </g>
              </svg>

              {flowchart.nodes.map((node) => (
                <div
                  aria-label={`${node.type.replaceAll("-", " ")}: ${node.label.replace("\n", " ")}`}
                  className={`flow-node${node.type === "decision" ? " decision-node" : ""}`}
                  key={node.id}
                  role="group"
                  style={{
                    left: `${node.position.x / 9}%`,
                    top: `${node.position.y}px`,
                  }}
                >
                  <FlowchartSymbol type={node.type} label={node.label} />
                </div>
              ))}
              <span className="canvas-caption">
                {flowchart.title.toUpperCase()} <span>·</span> {flowchart.nodes.length} STEPS
              </span>
            </div>
          </div>
          <footer className="editor-footer">
            <span>
              <span className="footer-pulse" /> SAMPLE PREVIEW
            </span>
            <span>Preview only · uploaded scripts aren&apos;t executed</span>
          </footer>
        </section>

        <aside
          className={`symbols-sidebar${symbolsOpen ? "" : " is-collapsed"}`}
          aria-label="Flowchart symbols"
        >
          <button
            aria-controls="symbols-content"
            aria-expanded={symbolsOpen}
            aria-label={`${symbolsOpen ? "Collapse" : "Expand"} symbols panel`}
            className="panel-toggle symbols-panel-toggle"
            onClick={() => setSymbolsOpen((open) => !open)}
            type="button"
          >
            <Icon name="panel-right" size={17} />
          </button>
          {symbolsOpen && (
            <div className="symbols-content" id="symbols-content">
              <div className="symbols-heading">
                <span className="eyebrow">SYMBOLS</span>
                <h2>Flowchart symbols</h2>
                <p>Common shapes and matching pseudocode examples.</p>
              </div>
              <div className="symbol-list">
                {flowchartSymbols.map((symbol) => (
                  <article className="symbol-card" key={symbol.type}>
                    <div className="symbol-card-icon">
                      <FlowchartSymbol
                        label={symbol.label}
                        type={symbol.type}
                      />
                    </div>
                    <div className="symbol-card-copy">
                      <h3>{symbol.name}</h3>
                      <code>{symbol.example}</code>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )}
        </aside>
          </>
        )}
      </section>
    </main>
  );
}

export default App;
