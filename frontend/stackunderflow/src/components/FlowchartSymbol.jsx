function SymbolShape({ type, label }) {
  const lines = label.split('\n')
  const firstLineY = lines.length > 1 ? 37 : 43

  return (
    <svg className={`symbol-svg symbol-${type}`} viewBox="0 0 260 76" preserveAspectRatio="none" aria-hidden="true" focusable="false">
      {type === 'terminator' && <rect x="18" y="8" width="224" height="60" rx="30" />}
      {type === 'process' && <rect x="18" y="8" width="224" height="60" rx="10" />}
      {type === 'decision' && <path d="M130 3 254 38 130 73 6 38Z" />}
      {type === 'data' && <path d="M43 8H244L217 68H16Z" />}
      {type === 'document' && <path d="M20 8H240V55c-19 0-19 13-38 13s-19-13-38-13-19 13-37 13-19-13-38-13-19 13-39 13Z" />}
      {type === 'predefined-process' && (
        <>
          <rect x="18" y="8" width="224" height="60" rx="8" />
          <path className="symbol-detail" d="M40 9v58M220 9v58" />
        </>
      )}
      {type === 'preparation' && <path d="M44 8H216L244 38 216 68H44L16 38Z" />}
      {type === 'connector' && <circle cx="130" cy="38" r="30" />}
      {lines.map((line, index) => (
        <text key={`${line}-${index}`} x="130" y={firstLineY + index * 15}>{line}</text>
      ))}
    </svg>
  )
}

export function FlowchartSymbol({ type, label }) {
  return <SymbolShape type={type} label={label} />
}
