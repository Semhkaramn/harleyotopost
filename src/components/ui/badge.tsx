import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "destructive" | "outline" | "success";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <div
      className={cn(
        "inline-flex items-center rounded-full px-3 py-1 text-xs font-semibold transition-colors",
        {
          "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30":
            variant === "default",
          "bg-zinc-700/50 text-zinc-300 border border-zinc-600":
            variant === "secondary",
          "bg-red-500/20 text-red-400 border border-red-500/30":
            variant === "destructive",
          "border border-zinc-600 text-zinc-400": variant === "outline",
          "bg-green-500/20 text-green-400 border border-green-500/30":
            variant === "success",
        },
        className
      )}
      {...props}
    />
  );
}

export { Badge };
