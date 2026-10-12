import { type FC, type ComponentProps } from "react";
import { cn } from "@/lib/utils";

export type SurfaceBadgeProps = ComponentProps<"span"> & {
  className?: string;
};

export const SurfaceBadge: FC<SurfaceBadgeProps> = ({
  className,
  children,
  ...props
}) => {
  return (
    <span
      className={cn(
        "px-1.5 py-0.5 rounded-full bg-[var(--secondary)] border border-[var(--border)] font-mono text-[10px] text-[var(--muted-foreground)] tabular-nums",
        className
      )}
      {...props}
    >
      {children}
    </span>
  );
};
