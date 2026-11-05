import React, { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react';

/* ─────────────────────────────────────────────────────────
 * THINKING — expandable agent trace, four variants
 *
 *   Steps      step list with spinner → muted checks
 *   Reasoning  prose reasoning that expands, then settles
 *   Search     web-search trace: query + sources read
 *   Coding     tool trace: files read, edits, commands
 *
 * The trace runs once, settles, and remains expandable.
 * ───────────────────────────────────────────────────────── */

const STAGES = [800, 600, 1800, 2600, 1600];

function useSequence(steps: number[]) {
  const [stage, setStage] = useState(0);
  useEffect(() => {
    if (stage >= steps.length - 1) return;
    const t = setTimeout(() => setStage((s) => s + 1), steps[stage]);
    return () => clearTimeout(t);
  }, [stage, steps]);
  return stage;
}

export type TraceRow = {
  primary: string;
  secondary?: string;
  mono?: boolean;
  add?: number;
  del?: number;
  href?: string;
};

const VARIANTS: Record<
  string,
  { active: string; done: string; rows: TraceRow[]; query?: string }
> = {
  Steps: {
    active: "Thinking",
    done: "Thought for 4 seconds",
    rows: [
      { primary: "Reading audio buffer logs" },
      { primary: "Checking WebSocket frame underrun rate" },
      { primary: "Adjusting duplex buffer depth to 120ms", secondary: "stream_sink.py:42" },
      { primary: "Validating low latency audio synchronization" },
    ],
  },
  Reasoning: {
    active: "Thinking",
    done: "Thought for 4 seconds",
    rows: [
      { primary: "WebSocket duplex underruns were triggered by a 50ms buffer bottleneck." },
      { primary: "Increasing buffer depth to 120ms eliminates packet drops while preserving sub-15ms roundtrip." },
    ],
  },
  Search: {
    active: "Searching knowledge base",
    done: "Searched telemetry docs",
    query: "core audio duplex buffer threshold",
    rows: [
      { primary: "Core Audio Daemon API", secondary: "docs.zezo.internal" },
      { primary: "WebSocket Frame Streaming Guide", secondary: "audio.spec" },
    ],
  },
  Coding: {
    active: "Running tools",
    done: "Ran 1 tool",
    rows: [
      { primary: "Patch", secondary: "stream_sink.py:42", mono: true, add: 1, del: 1 },
    ],
  },
};

function Dot({ tone }: { tone: string }) {
  return (
    <span className={`trace-dot ${tone}`}>
      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="9" />
        <path d="M3.5 12h17M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18" />
      </svg>
    </span>
  );
}

const TONES = ["dot-accent", "dot-orange", "dot-green"];

interface ThinkingStateProps {
  variant?: 'Steps' | 'Reasoning' | 'Search' | 'Coding';
  onSettled?: () => void;
  rows?: TraceRow[];
  active?: string;
  done?: string;
  icon?: ReactNode;
}

export const ThinkingState: React.FC<ThinkingStateProps> = ({
  variant = "Steps",
  onSettled,
  rows,
  active,
  done,
  icon,
}) => {
  const stage = useSequence(STAGES);
  const [manualExpanded, setManualExpanded] = useState<boolean | null>(null);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const base = VARIANTS[variant] ?? VARIANTS.Steps;
  const v = {
    ...base,
    rows: rows ?? base.rows,
    active: active ?? base.active,
    done: done ?? base.done,
  };
  const autoExpanded = stage >= 1 && stage < 4;
  const expanded = manualExpanded ?? autoExpanded;
  const working = stage < 3;
  const visible = stage < 2 ? 0 : stage === 2 ? Math.min(2, v.rows.length) : v.rows.length;
  const traceRef = useRef<HTMLDivElement>(null);
  const [lineHeight, setLineHeight] = useState(0);

  useLayoutEffect(() => {
    if (traceRef.current) setLineHeight(traceRef.current.offsetHeight);
  }, [visible, expanded, variant, stage]);

  /* let embedders sequence content after the trace settles */
  const settledRef = useRef(false);
  useEffect(() => {
    if (working || settledRef.current) return;
    settledRef.current = true;
    onSettled?.();
  }, [working, onSettled]);

  return (
    <div
      key={variant}
      className="thinking-trace-wrapper"
    >
      {/* header button — shared across variants */}
      <button
        type="button"
        aria-expanded={expanded}
        onClick={() => setManualExpanded((current) => !(current ?? autoExpanded))}
        className="thinking-header-btn"
      >
        {icon ? (
          <span className="thinking-header-icon" style={{ color: working ? "var(--ink-2)" : "var(--ink-3)" }}>
            {icon}
          </span>
        ) : (
          <svg width="15" height="15" viewBox="0 0 24 24" fill={working ? "var(--ink-2)" : "var(--ink-3)"} className="thinking-header-icon">
            <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />
          </svg>
        )}
        <span role="status" className="thinking-status-wrapper">
          {working ? (
            <span className="thinking-status-shimmer">
              {v.active}
            </span>
          ) : (
            <span className="thinking-status-done">
              {v.done}
            </span>
          )}
        </span>
        <svg
          width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--ink-3)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"
          className="thinking-chevron"
          style={{ transform: expanded ? "rotate(180deg)" : "rotate(0)" }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      {/* expandable trace */}
      <div
        className="thinking-trace-grid"
        style={{
          gridTemplateRows: expanded ? "1fr" : "0fr",
          opacity: expanded ? 1 : 0,
        }}
      >
        <div className="thinking-trace-overflow">
          <div className="thinking-trace-content">
            <span
              aria-hidden
              className="thinking-trace-line"
              style={{ height: lineHeight ? lineHeight - 2 : 0 }}
            />
            <div ref={traceRef} className="thinking-rows-list">
              {v.query && (
                <div className="trace-query-row">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--ink-3)" strokeWidth="2" strokeLinecap="round" className="shrink-0">
                    <circle cx="11" cy="11" r="7" />
                    <path d="M21 21l-4.3-4.3" />
                  </svg>
                  <span className="trace-query-text">{v.query}</span>
                </div>
              )}
              {v.rows.slice(0, visible).map((row, i) => {
                const content = (
                  <>
                    {variant === "Search" && <Dot tone={TONES[i % 3]} />}
                    {variant === "Steps" && (
                      i < visible - 1 || !working ? (
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--ink-3)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                          <path d="M20 6L9 17l-5-5" />
                        </svg>
                      ) : (
                        <span className="trace-spinner" />
                      )
                    )}
                    <span className={`trace-row-primary ${variant === "Reasoning" ? "reasoning-text" : ""}`}>
                      {row.primary}
                    </span>
                    {row.secondary && (
                      <span className={`trace-row-secondary ${row.mono ? "mono-text" : ""}`}>
                        {row.secondary}
                      </span>
                    )}
                    {row.add !== undefined && (
                      <span className="trace-diff-tag">
                        <span className="diff-add">+{row.add}</span>{" "}
                        <span className="diff-del">−{row.del}</span>
                      </span>
                    )}
                  </>
                );

                if (variant === "Search") {
                  return (
                    <a
                      key={row.primary}
                      href={row.href || '#'}
                      target="_blank"
                      rel="noreferrer"
                      className="trace-row-item hover-link"
                    >
                      {content}
                    </a>
                  );
                }

                if (variant === "Coding") {
                  const selected = selectedTool === row.primary;
                  return (
                    <button
                      key={row.primary}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => setSelectedTool(selected ? null : row.primary)}
                      className={`trace-row-item ${selected ? "selected" : ""}`}
                    >
                      {content}
                    </button>
                  );
                }

                return (
                  <div key={row.primary} className="trace-row-item">
                    {content}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

