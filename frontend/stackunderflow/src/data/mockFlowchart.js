export const flowchartSymbols = [
  {
    type: "terminator",
    name: "Terminator",
    label: "Start",
    example: "START / END",
  },
  {
    type: "process",
    name: "Process",
    label: "Action",
    example: "value = value + 1",
  },
  {
    type: "decision",
    name: "Decision",
    label: "Condition?",
    example: "if value > 0",
  },
  {
    type: "data",
    name: "Input / output",
    label: "Read value",
    example: "value = input()",
  },
  {
    type: "document",
    name: "Document",
    label: "Report",
    example: "write_report()",
  },
  {
    type: "predefined-process",
    name: "Predefined process",
    label: "Subroutine",
    example: "validate(value)",
  },
  {
    type: "preparation",
    name: "Preparation",
    label: "Initialize",
    example: "value = 0",
  },
  {
    type: "connector",
    name: "On-page connector",
    label: "A",
    example: "Continue at A",
  },
];

function createNumberCheckFlowchart(fileName) {
  return {
    title: fileName || "Number check",
    description: "Static number-check preview. Uploaded code is not analyzed yet.",
    sourceFile: fileName,
    isMockOutput: true,
    nodes: [
      { id: "start", type: "terminator", label: "Start", position: { x: 450, y: 14 } },
      { id: "input", type: "data", label: "Enter a number", position: { x: 450, y: 86 } },
      { id: "process", type: "process", label: "Read the value", position: { x: 450, y: 164 } },
      { id: "decision", type: "decision", label: "Is it positive?", position: { x: 450, y: 237 } },
      { id: "positive", type: "process", label: "Show positive", position: { x: 250, y: 390 } },
      { id: "other", type: "process", label: "Show zero / negative", position: { x: 650, y: 390 } },
      { id: "end", type: "terminator", label: "Finish", position: { x: 450, y: 490 } },
    ],
    connections: [
      { path: "M450 82V86" },
      { path: "M450 154V164" },
      { path: "M450 232V237" },
      { path: "M450 360V378H250V390", label: { x: 346, y: 378, text: "Yes" } },
      { path: "M450 378H650V390", label: { x: 554, y: 378, text: "No" } },
      { path: "M250 466V480H450V490" },
      { path: "M650 466V480H450" },
    ],
  };
}

export const initialFlowchart = createNumberCheckFlowchart("number_check.py");

export { createNumberCheckFlowchart };
