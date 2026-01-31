import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "./button"

/**
 * Select Component
 * Accessible dropdown with keyboard navigation
 */
const selectVariants = cva(
  "flex w-full appearance-none rounded-lg border bg-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "border-slate-600 bg-slate-800/50 text-slate-100 focus-visible:border-[#3B82F6] focus-visible:ring-[#3B82F6]",
        error:
          "border-red-500 bg-red-500/10 text-slate-100 focus-visible:border-red-500 focus-visible:ring-red-500",
      },
      size: {
        sm: "h-8 px-3 pr-8 text-sm",
        md: "h-12 px-4 pr-10 text-base",
        lg: "h-14 px-4 pr-12 text-lg",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
)

export interface SelectOption {
  value: string
  label: string
  disabled?: boolean
}

export interface SelectProps
  extends Omit<React.SelectHTMLAttributes<HTMLSelectElement>, "size">,
    VariantProps<typeof selectVariants> {
  options: SelectOption[]
  error?: string
  label?: string
  helperText?: string
  placeholder?: string
}

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, variant, size, error, label, helperText, options, placeholder, id, ...props }, ref) => {
    const selectId = id || React.useId()
    const hasError = !!error || variant === "error"

    return (
      <div className="w-full space-y-2">
        {label && (
          <label
            htmlFor={selectId}
            className="text-sm font-medium text-slate-300"
          >
            {label}
            {props.required && (
              <span className="ml-1 text-red-500" aria-hidden="true">
                *
              </span>
            )}
          </label>
        )}
        <div className="relative">
          <select
            id={selectId}
            className={cn(
              selectVariants({ variant: hasError ? "error" : variant, size, className })
            )}
            ref={ref}
            aria-invalid={hasError}
            aria-describedby={
              error
                ? `${selectId}-error`
                : helperText
                ? `${selectId}-helper`
                : undefined
            }
            {...props}
          >
            {placeholder && (
              <option value="" disabled>
                {placeholder}
              </option>
            )}
            {options.map((option) => (
              <option key={option.value} value={option.value} disabled={option.disabled}>
                {option.label}
              </option>
            ))}
          </select>
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-slate-400">
            <svg
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        </div>
        {error && (
          <p
            id={`${selectId}-error`}
            className="text-sm text-red-400 flex items-center gap-1"
            role="alert"
          >
            <svg
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            {error}
          </p>
        )}
        {helperText && !error && (
          <p id={`${selectId}-helper`} className="text-sm text-slate-500">
            {helperText}
          </p>
        )}
      </div>
    )
  }
)
Select.displayName = "Select"

export { Select, selectVariants }
