import { type FC, type ComponentProps } from "react";
import { cn } from "@/lib/utils";

export type ShimmerLabelProps = ComponentProps<"span"> & {
 className?: string;
};

export const ShimmerLabel: FC<ShimmerLabelProps> = ({
 className,
 children,
 ...props
}) => {
 return (
 <span
 className={cn(
 "inline-block animate-in fade-in duration-150 font-medium text-[var(--foreground)]",
 className
 )}
 {...props}
 >
 {children}
 </span>
 );
};
