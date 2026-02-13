"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

interface SelectProps {
  value?: string;
  onValueChange?: (value: string) => void;
  children: React.ReactNode;
  placeholder?: string;
  className?: string;
}

const Select = ({ value, onValueChange, children, placeholder, className }: SelectProps) => {
  return (
    <select
      value={value}
      onChange={(e) => onValueChange?.(e.target.value)}
      className={cn(
        "flex h-11 w-full rounded-lg border-2 border-zinc-700 bg-zinc-800/50 px-4 py-2 text-sm text-zinc-100 transition-all duration-200",
        "focus:outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20",
        "hover:border-zinc-600",
        "disabled:cursor-not-allowed disabled:opacity-50",
        "appearance-none cursor-pointer",
        className
      )}
    >
      {placeholder && (
        <option value="" disabled>
          {placeholder}
        </option>
      )}
      {children}
    </select>
  );
};

const SelectOption = ({ value, children }: { value: string; children: React.ReactNode }) => (
  <option value={value} className="bg-zinc-800 text-zinc-100">
    {children}
  </option>
);

export { Select, SelectOption };
