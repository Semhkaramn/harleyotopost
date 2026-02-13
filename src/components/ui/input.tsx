import * as React from "react";
import { cn } from "@/lib/utils";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-11 w-full rounded-lg border-2 border-zinc-700 bg-zinc-800/50 px-4 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 transition-all duration-200",
          "focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20",
          "hover:border-zinc-600",
          "disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Input.displayName = "Input";

export { Input };
