import * as React from "react"

import { cn } from "@/lib/utils"

export interface InputProps extends React.ComponentProps<"input"> {
  error?: boolean
}

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, error, ...props }, ref) => {
    return (
      <input
        type={type}
        aria-invalid={error ? "true" : undefined}
        className={cn(
          "flex h-9 w-full rounded-md border bg-transparent px-3 py-1 text-sm",
          "transition-colors placeholder:text-muted-foreground",
          "file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-0",
          "disabled:cursor-not-allowed disabled:opacity-50",
          "read-only:opacity-70 read-only:cursor-default",
          error
            ? "border-destructive focus-visible:ring-destructive/40 text-destructive placeholder:text-destructive/50"
            : "border-input hover:border-ring/30",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
