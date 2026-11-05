import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";

/* ─────────────────────────────────────────────────────────
 * TOOL CHIPS
 * An agent run as compact rows: tool calls with inline
 * chips, then file-diff chips summarizing the edits.
 * Hover a row to reveal its chevron; every row expands
 * to show what the tool actually did.
 * ───────────────────────────────────────────────────────── */

const STEP_MS = 600;

const Icons: Record<string, React.ReactNode> = {
  think: <path d="M12 2l2.4 7.2L22 12l-7.6 2.8L12 22l-2.4-7.2L2 12l7.6-2.8z" />,
  write: <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 3a2.8 2.8 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5z" /></g>,
  run: <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 17l6-5-6-5M12 19h8" /></g>,
  read: <g fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /></g>,
};

export type ToolDetailLine = { text: string; tone?: "add" };

export type ToolStep = {
  icon: string;
  label: string;
  chip: string;
  mono: boolean;
  detailMono: boolean;
  detail: ToolDetailLine[];
};

export type ToolDiff = { file: string; add: number; del: number };

export type ToolDiffLine = { text: string; tone: "add" | "del" | "ctx" };

export type ToolChipsLabels = {
  header: string;
  more: string;
};

const DEFAULT_LABELS: ToolChipsLabels = {
  header: "2 tool calls, 1 file edited",
  more: "+2 more",
};

const ROWS: ToolStep[] = [
  {
    icon: "think", 
    label: "Telemetry", 
    chip: "Inspecting Core Audio buffer underruns…", 
    mono: false, 
    detailMono: false,
    detail: [
      { text: "Ring buffer threshold set to 50ms (causing frame drop in duplex mode)." },
      { text: "Recommended duplex depth is 120ms to eliminate drop rate." },
    ],
  },
  {
    icon: "write", 
    label: "Patch audio sink", 
    chip: "audio_daemon/stream_sink.py:42", 
    mono: true, 
    detailMono: true,
    detail: [
      { text: "- StreamSink.BUFFER_MS = 50", tone: undefined },
      { text: "+ StreamSink.BUFFER_MS = 120 # increased buffer depth", tone: "add" },
    ],
  },
  {
    icon: "run", 
    label: "Verify daemon", 
    chip: "audio_daemon status", 
    mono: true, 
    detailMono: true,
    detail: [
      { text: "✓ audio_daemon online (PID 1420)" },
      { text: "✓ zero dropped frames reported" },
    ],
  },
];

const DIFFS: ToolDiff[] = [
  { file: "stream_sink.py", add: 1, del: 1 },
];

/* hovering a file chip opens its diff — green added, red removed */
const DIFF_LINES: Record<string, ToolDiffLine[]> = {
  "stream_sink.py": [
    { text: "class StreamSink:", tone: "ctx" },
    { text: "  BUFFER_MS = 50", tone: "del" },
    { text: "  BUFFER_MS = 120 # increased depth", tone: "add" },
    { text: "  SAMPLE_RATE = 48000", tone: "ctx" },
  ],
};

export interface ToolChipsProps {
  steps?: ToolStep[];
  diffs?: ToolDiff[];
  diffLines?: Record<string, ToolDiffLine[]>;
  labels?: Partial<ToolChipsLabels>;
  className?: string;
  onOpenChange?: (open: boolean) => void;
  onToggleRow?: (label: string, open: boolean) => void;
}

export const ToolChips: React.FC<ToolChipsProps> = ({
  steps = ROWS,
  diffs = DIFFS,
  diffLines = DIFF_LINES,
  labels,
  className,
  onOpenChange,
  onToggleRow,
}) => {
  const copy = { ...DEFAULT_LABELS, ...labels };
  const [step, setStep] = useState(0);
  const [open, setOpen] = useState(true);
  const [openRows, setOpenRows] = useState<Set<string>>(new Set());

  const [preview, setPreview] = useState<{
    file: string;
    x: number;
    top?: number;
    bottom?: number;
  } | null>(null);

  const openPreview = (file: string) => (event: React.SyntheticEvent) => {
    const rect = (event.currentTarget as Element).closest("[data-diffchip]")!.getBoundingClientRect();
    const previewHeight = 38 + (diffLines[file]?.length ?? 0) * 19;
    const fitsBelow = rect.bottom + 6 + previewHeight <= window.innerHeight - 12;
    setPreview({
      file,
      x: Math.max(12, Math.min(rect.left, window.innerWidth - 300)),
      ...(fitsBelow
        ? { top: rect.bottom + 6 }
        : { bottom: window.innerHeight - rect.top + 6 }),
    });
  };

  const closePreview = (file: string) => () =>
    setPreview((current) => (current?.file === file ? null : current));

  const total = steps.length + 1; // rows, then diff chips

  useEffect(() => {
    if (step >= total) return;
    const t = setTimeout(() => setStep((s) => s + 1), STEP_MS);
    return () => clearTimeout(t);
  }, [step, total]);

  const toggleRow = (label: string) =>
    setOpenRows((current) => {
      const next = new Set(current);
      next.has(label) ? next.delete(label) : next.add(label);
      onToggleRow?.(label, next.has(label));
      return next;
    });

  return (
    <div className={`tool-chips-wrapper${className ? ` ${className}` : ""}`}>
      {/* collapsed run header */}
      <button
        type="button"
        aria-expanded={open}
        onClick={() =>
          setOpen((current) => {
            onOpenChange?.(!current);
            return !current;
          })
        }
        className="tool-chips-header-btn"
      >
        <svg 
          width="12" 
          height="12" 
          viewBox="0 0 24 24" 
          fill="none" 
          stroke="currentColor" 
          strokeWidth="2.2" 
          strokeLinecap="round" 
          strokeLinejoin="round" 
          className="tool-chips-chevron"
          style={{ transform: open ? "rotate(0deg)" : "rotate(-90deg)" }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
        <span className="tool-chips-header-label">{copy.header}</span>
      </button>

      {/* tool call rows */}
      <div 
        className="tool-chips-grid" 
        style={{ gridTemplateRows: open ? "1fr" : "0fr", opacity: open ? 1 : 0 }}
      >
        <div className="tool-chips-overflow">
          <div className="tool-chips-rows">
            {steps.slice(0, step).map((row) => {
              const rowOpen = openRows.has(row.label);
              return (
                <div key={row.label} className="tool-step-item">
                  <button
                    type="button"
                    aria-expanded={rowOpen}
                    onClick={() => toggleRow(row.label)}
                    className="tool-step-btn group/row"
                  >
                    <span className="tool-step-icon-wrap">
                      <svg
                        width="13" 
                        height="13" 
                        viewBox="0 0 24 24" 
                        fill={row.icon === "think" ? "currentColor" : "none"} 
                        stroke="currentColor"
                        className={`tool-step-icon ${rowOpen ? "opacity-0" : ""}`}
                      >
                        {Icons[row.icon]}
                      </svg>
                      <svg
                        width="12" 
                        height="12" 
                        viewBox="0 0 24 24" 
                        fill="none" 
                        stroke="currentColor" 
                        strokeWidth="2.2" 
                        strokeLinecap="round" 
                        strokeLinejoin="round"
                        className={`tool-step-chevron ${rowOpen ? "opacity-100" : "opacity-0"}`}
                        style={{ transform: rowOpen ? "rotate(0deg)" : "rotate(-90deg)" }}
                      >
                        <path d="M6 9l6 6 6-6" />
                      </svg>
                    </span>
                    <span className="tool-step-label">{row.label}</span>
                    <span
                      className={`tool-step-chip ${row.mono ? "mono-text" : ""}`}
                    >
                      {row.chip}
                    </span>
                  </button>

                  {/* expanded detail */}
                  <div
                    className="tool-step-detail-grid"
                    style={{ gridTemplateRows: rowOpen ? "1fr" : "0fr", opacity: rowOpen ? 1 : 0 }}
                  >
                    <div className="tool-step-detail-overflow">
                      <div className="tool-step-detail-list">
                        {row.detail.map((line) => (
                          <span
                            key={line.text}
                            className={`tool-step-detail-line ${row.detailMono ? "mono-text" : ""} ${line.tone === "add" ? "text-add" : ""}`}
                          >
                            {line.text}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* file-diff chips */}
          {step >= total && (
            <div className="tool-diffs-container">
              {diffs.map((d) => (
                <span
                  key={d.file}
                  data-diffchip
                  className="diff-chip-wrapper"
                  onMouseEnter={openPreview(d.file)}
                  onMouseLeave={closePreview(d.file)}
                >
                  <button
                    type="button"
                    aria-expanded={preview?.file === d.file}
                    aria-label={`Show diff for ${d.file}`}
                    onFocus={openPreview(d.file)}
                    onBlur={closePreview(d.file)}
                    className="diff-chip-btn"
                  >
                    <span className="diff-file-name">{d.file}</span>
                    <span className="diff-count-add">+{d.add}</span>
                    {d.del > 0 && <span className="diff-count-del">−{d.del}</span>}
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      </div>

      {preview && typeof document !== "undefined" && createPortal(
        <div
          className="diff-preview-popup"
          style={{
            left: preview.x,
            top: preview.top,
            bottom: preview.bottom,
            transformOrigin: preview.top === undefined ? "bottom left" : "top left",
          }}
        >
          <div className="diff-preview-header">
            <span className="diff-preview-file">{preview.file}</span>
            <span className="diff-preview-stats">
              <span className="diff-count-add">+{diffs.find((diff) => diff.file === preview.file)?.add}</span>
              {(diffs.find((diff) => diff.file === preview.file)?.del ?? 0) > 0 && (
                <span className="diff-count-del"> −{diffs.find((diff) => diff.file === preview.file)?.del}</span>
              )}
            </span>
          </div>
          <div className="diff-preview-lines">
            {(diffLines[preview.file] ?? []).map((line, index) => (
              <div
                key={index}
                className={`diff-line-entry ${
                  line.tone === "add"
                    ? "tone-add"
                    : line.tone === "del"
                      ? "tone-del"
                      : "tone-ctx"
                }`}
              >
                <span className="diff-sym">{line.tone === "add" ? "+" : line.tone === "del" ? "−" : " "}</span>
                <span className="diff-text">{line.text}</span>
              </div>
            ))}
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
};

