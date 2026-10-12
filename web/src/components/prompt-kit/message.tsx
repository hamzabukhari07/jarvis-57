"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface MessageProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function Message({ children, className, ...props }: MessageProps) {
  return (
    <div
      className={cn("flex w-full gap-3 py-2 items-start", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export interface MessageAvatarProps extends React.HTMLAttributes<HTMLDivElement> {
  src?: string;
  alt?: string;
  fallback?: string;
  name?: string;
  children?: React.ReactNode;
}

export function MessageAvatar({
  src,
  alt = "Avatar",
  fallback = "AI",
  name,
  children,
  className,
  ...props
}: MessageAvatarProps) {
  const [imageError, setImageError] = React.useState(false);

  return (
    <div
      className={cn(
        "relative flex h-8 w-8 shrink-0 overflow-hidden rounded-full border border-[var(--border)] bg-[var(--card)] items-center justify-center text-xs font-semibold text-[var(--foreground)] shadow-xs select-none",
        className
      )}
      {...props}
    >
      {children ? (
        children
      ) : src && !imageError ? (
        <img
          src={src}
          alt={alt}
          onError={() => setImageError(true)}
          className="aspect-square h-full w-full object-cover"
        />
      ) : (
        <span className="font-mono text-[11px] uppercase text-[var(--muted-foreground)]">
          {fallback}
        </span>
      )}
    </div>
  );
}

export interface MessageContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children?: React.ReactNode;
  markdown?: boolean;
}

export function MessageContent({
  children,
  markdown = false,
  className,
  ...props
}: MessageContentProps) {
  return (
    <div
      className={cn(
        "text-xs leading-relaxed max-w-2xl break-words",
        markdown
          ? "prose prose-xs dark:prose-invert max-w-none text-[var(--foreground)]"
          : "rounded-2xl px-4 py-2.5 bg-primary text-primary-foreground font-normal shadow-xs",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export interface MessageActionsProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export function MessageActions({ children, className, ...props }: MessageActionsProps) {
  return (
    <div
      className={cn(
        "flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
