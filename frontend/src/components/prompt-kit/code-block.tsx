"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { Check, Copy } from "lucide-react";

export interface CodeBlockProps extends React.HTMLAttributes<HTMLDivElement> {
 children?: React.ReactNode;
}

export function CodeBlock({ children, className, ...props }: CodeBlockProps) {
 return (
 <div
 className={cn(
 "relative rounded-xl border border-[var(--border)] bg-[var(--card)]/90 overflow-hidden font-mono text-xs",
 className
 )}
 {...props}
 >
 {children}
 </div>
 );
}

export interface CodeBlockCodeProps extends React.HTMLAttributes<HTMLPreElement> {
 code: string;
 language?: string;
}

export function CodeBlockCode({
 code,
 language,
 className,
 ...props
}: CodeBlockCodeProps) {
 const [copied, setCopied] = React.useState(false);

 const handleCopy = () => {
 navigator.clipboard.writeText(code);
 setCopied(true);
 setTimeout(() => setCopied(false), 2000);
 };

 return (
 <div className="relative group">
 {/* Top Header bar if language is defined */}
 <div className="flex items-center justify-between px-3 py-1.5 border-b border-[var(--border)]/40 bg-[var(--secondary)]/30 text-[10px] text-[var(--muted-foreground)]">
 <span className="uppercase font-semibold tracking-wider">{language || "text"}</span>
 <button
 type="button"
 onClick={handleCopy}
 className="flex items-center gap-1 hover:text-[var(--foreground)] transition-colors p-0.5 rounded cursor-pointer"
 title="Copy code"
 >
 {copied ? (
 <>
 <Check className="size-3 text-emerald-400" />
 <span>Copied</span>
 </>
 ) : (
 <>
 <Copy className="size-3" />
 <span>Copy</span>
 </>
 )}
 </button>
 </div>

 <pre
 className={cn(
 "p-3 overflow-x-auto text-xs text-[var(--foreground)] font-mono leading-relaxed",
 className
 )}
 {...props}
 >
 <code>{code}</code>
 </pre>
 </div>
 );
}
