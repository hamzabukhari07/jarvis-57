"use client";

import * as React from "react";
import { cn } from "@/lib/utils";
import { ChevronDown, Circle } from "lucide-react";

export type ChainOfThoughtItemProps = React.ComponentProps<"div">;

export const ChainOfThoughtItem = ({
 children,
 className,
 ...props
}: ChainOfThoughtItemProps) => (
 <div className={cn("text-[var(--muted-foreground)] text-xs leading-relaxed", className)} {...props}>
 {children}
 </div>
);

export interface ChainOfThoughtTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
 leftIcon?: React.ReactNode;
 swapIconOnHover?: boolean;
}

export const ChainOfThoughtTrigger = ({
 children,
 className,
 leftIcon,
 swapIconOnHover = true,
 onClick,
 ...props
}: ChainOfThoughtTriggerProps) => {
 return (
 <button
 type="button"
 className={cn(
 "group text-[var(--muted-foreground)] hover:text-[var(--foreground)] flex cursor-pointer items-center justify-start gap-1.5 text-left text-xs font-medium transition-colors w-full py-1",
 className
 )}
 onClick={onClick}
 {...props}
 >
 <div className="flex items-center gap-2 flex-1 min-w-0">
 {leftIcon ? (
 <span className="relative inline-flex size-4 shrink-0 items-center justify-center text-[var(--accent)]">
 <span
 className={cn(
 "transition-opacity",
 swapIconOnHover && "group-hover:opacity-0"
 )}
 >
 {leftIcon}
 </span>
 {swapIconOnHover && (
 <ChevronDown className="absolute size-3.5 opacity-0 transition-opacity group-hover:opacity-100 group-data-[state=open]:rotate-180" />
 )}
 </span>
 ) : (
 <span className="relative inline-flex size-4 shrink-0 items-center justify-center text-[var(--muted-foreground)]">
 <Circle className="size-1.5 fill-current" />
 </span>
 )}
 <span className="truncate">{children}</span>
 </div>
 {!leftIcon && (
 <ChevronDown className="size-3.5 shrink-0 transition-transform group-data-[state=open]:rotate-180" />
 )}
 </button>
 );
};

export interface ChainOfThoughtContentProps extends React.ComponentProps<"div"> {
 isOpen?: boolean;
}

export const ChainOfThoughtContent = ({
 children,
 className,
 isOpen = true,
 ...props
}: ChainOfThoughtContentProps) => {
 if (!isOpen) return null;

 return (
 <div
 className={cn(
 "text-[var(--foreground)] overflow-hidden animate-in fade-in-50 duration-200",
 className
 )}
 {...props}
 >
 <div className="grid grid-cols-[min-content_minmax(0,1fr)] gap-x-3">
 <div className="bg-[var(--border)] ml-1.5 h-full w-px group-data-[last=true]:hidden" />
 <div className="ml-1.5 h-full w-px bg-transparent group-data-[last=false]:hidden" />
 <div className="mt-1 space-y-1.5 pb-2">{children}</div>
 </div>
 </div>
 );
};

export type ChainOfThoughtStepProps = React.ComponentProps<"div"> & {
 children: React.ReactNode;
 isLast?: boolean;
 defaultOpen?: boolean;
};

export const ChainOfThoughtStep = ({
 children,
 className,
 isLast = false,
 defaultOpen = true,
 ...props
}: ChainOfThoughtStepProps) => {
 const [isOpen, setIsOpen] = React.useState(defaultOpen);

 // Clone trigger and content to pass isOpen/onToggle state
 const childrenWithProps = React.Children.map(children, (child) => {
 if (!React.isValidElement(child)) return child;

 if (child.type === ChainOfThoughtTrigger) {
 return React.cloneElement(child as React.ReactElement<any>, {
 onClick: (e: React.MouseEvent) => {
 (child.props as any).onClick?.(e);
 setIsOpen((prev) => !prev);
 },
 "data-state": isOpen ? "open" : "closed",
 });
 }

 if (child.type === ChainOfThoughtContent) {
 return React.cloneElement(child as React.ReactElement<any>, {
 isOpen,
 });
 }

 return child;
 });

 return (
 <div
 className={cn("group flex flex-col", className)}
 data-last={isLast}
 data-state={isOpen ? "open" : "closed"}
 {...props}
 >
 {childrenWithProps}
 <div className="flex justify-start group-data-[last=true]:hidden">
 <div className="bg-[var(--border)] ml-1.5 h-2.5 w-px" />
 </div>
 </div>
 );
};

export type ChainOfThoughtProps = {
 children: React.ReactNode;
 className?: string;
};

export function ChainOfThought({ children, className }: ChainOfThoughtProps) {
 const childrenArray = React.Children.toArray(children);

 return (
 <div className={cn("space-y-0.5 w-full", className)}>
 {childrenArray.map((child, index) => (
 <React.Fragment key={index}>
 {React.isValidElement(child) &&
 React.cloneElement(
 child as React.ReactElement<ChainOfThoughtStepProps>,
 {
 isLast: index === childrenArray.length - 1,
 }
 )}
 </React.Fragment>
 ))}
 </div>
 );
}
