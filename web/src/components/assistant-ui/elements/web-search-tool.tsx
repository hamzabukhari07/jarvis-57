"use client";

import * as React from "react";
import { Search, Globe, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const SEARCH_SHIMMER_STYLE_ID = "an-web-search-shimmer-styles";
const SEARCH_SHIMMER_STYLES = `
@keyframes an-search-shimmer {
  from { background-position: 100% center; }
  to { background-position: 0% center; }
}
.an-search-shimmer {
  display: inline-flex;
  align-items: center;
  background-size: 250% 100%;
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
  background-image: linear-gradient(90deg, #a3a3a3 0%, #a3a3a3 40%, #525252 50%, #a3a3a3 60%, #a3a3a3 100%);
  background-repeat: no-repeat;
  animation: an-search-shimmer 1.2s linear infinite;
}
`;

let searchShimmerInjected = false;
function ensureSearchShimmerStyles() {
  if (typeof document === "undefined") return;
  if (searchShimmerInjected) return;
  if (document.getElementById(SEARCH_SHIMMER_STYLE_ID)) {
    searchShimmerInjected = true;
    return;
  }
  const el = document.createElement("style");
  el.id = SEARCH_SHIMMER_STYLE_ID;
  el.textContent = SEARCH_SHIMMER_STYLES;
  document.head.appendChild(el);
  searchShimmerInjected = true;
}

export interface WebSearchSource {
  title: string;
  url?: string;
  domain?: string;
  status?: "pending" | "done" | "searching";
}

export interface WebSearchToolProps {
  query?: string;
  sources?: WebSearchSource[];
  isSearching?: boolean;
  defaultOpen?: boolean;
  expanded?: boolean;
  onToggleExpand?: () => void;
  className?: string;
}

export const WebSearchTool = React.memo(function WebSearchTool({
  query,
  sources = [],
  isSearching = false,
  defaultOpen = true,
  expanded,
  onToggleExpand,
  className,
}: WebSearchToolProps) {
  React.useEffect(() => {
    ensureSearchShimmerStyles();
  }, []);

  const isControlled = expanded !== undefined;
  const [internalOpen, setInternalOpen] = React.useState(defaultOpen);
  const isOpen = isControlled ? !!expanded : internalOpen;

  const handleToggle = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (isControlled) {
      onToggleExpand?.();
    } else {
      setInternalOpen((v) => !v);
    }
  };

  const displayQuery = query || "web sources...";

  return (
    <div className={cn("flex flex-col gap-1.5 w-full my-2 select-none", className)}>
      {/* Header Button matching ThinkingTool style */}
      <button
        type="button"
        onClick={handleToggle}
        aria-expanded={isOpen}
        className="group inline-flex items-center self-start gap-2 rounded-[6px] bg-transparent border-0 p-0 m-0 text-left cursor-pointer"
      >
        <Search className="w-3.5 h-3.5 shrink-0 text-neutral-400 dark:text-neutral-500" />
        
        <div className="flex items-center gap-1.5 min-w-0 text-xs text-neutral-400 dark:text-neutral-400">
          <span className="font-[450] whitespace-nowrap">
            {isSearching ? (
              <span className="an-search-shimmer font-medium">Searching</span>
            ) : (
              <span>Searched</span>
            )}
          </span>
          <span className="text-neutral-200 dark:text-neutral-300 font-normal truncate max-w-[280px] sm:max-w-[420px]">
            &ldquo;{displayQuery}&rdquo;
          </span>
        </div>

        <ChevronDown
          className={cn(
            "w-3 h-3 shrink-0 text-neutral-400 dark:text-neutral-500 transition-transform duration-150 ease-out",
            isOpen ? "rotate-0" : "-rotate-90"
          )}
        />
      </button>

      {/* Expandable Sources Tree */}
      {isOpen && sources.length > 0 && (
        <div className="ml-1.5 pl-3 border-l border-neutral-700/60 dark:border-neutral-800 flex flex-col gap-1.5 pt-1 text-[11px]">
          {sources.map((s, idx) => {
            const isItemPending = s.status === "pending" || (isSearching && idx === sources.length - 1);
            const domain = s.domain || (s.url ? s.url.replace(/^https?:\/\//, '').split('/')[0] : 'web');

            return (
              <a
                key={idx}
                href={s.url || "#"}
                target="_blank"
                rel="noreferrer"
                className="group/item flex items-center gap-2 text-neutral-400 hover:text-neutral-200 transition-colors py-0.5 truncate"
              >
                {isItemPending ? (
                  <span className="w-3.5 h-3.5 shrink-0 rounded-full border border-dashed border-neutral-500 animate-spin" />
                ) : (
                  <Globe className="w-3.5 h-3.5 shrink-0 text-neutral-500 group-hover/item:text-neutral-300" />
                )}

                <span className="truncate font-normal text-neutral-300 group-hover/item:text-white">
                  {s.title}
                </span>

                <span className="text-neutral-600 dark:text-neutral-500 select-none">·</span>

                <span className="truncate text-[10px] text-neutral-500 dark:text-neutral-500 group-hover/item:text-neutral-400">
                  {s.url || domain}
                </span>
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
});
