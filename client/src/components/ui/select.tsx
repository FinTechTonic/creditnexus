import * as React from "react"
import { cn } from "@/lib/utils"

export interface SelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  onValueChange?: (value: string) => void
}

const SelectContext = React.createContext<{
  value?: string
  onValueChange?: (value: string) => void
}>({})

const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, children, value, onValueChange, onChange, ...props }, ref) => {
    const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
      if (onValueChange) {
        onValueChange(e.target.value)
      }
      if (onChange) {
        onChange(e)
      }
    }

    return (
      <SelectContext.Provider value={{ value, onValueChange }}>
        <select
          className={cn(
            "flex h-10 w-full rounded-md border border-[var(--color-input)] bg-[var(--color-background)] px-3 py-2 text-sm ring-offset-[var(--color-background)] file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-[var(--color-muted-foreground)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-ring)] focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
            className
          )}
          ref={ref}
          value={value}
          onChange={handleChange}
          {...props}
        >
          {children}
        </select>
      </SelectContext.Provider>
    )
  }
)
Select.displayName = "Select"

// SelectTrigger is a no-op for native select (just passes through)
const SelectTrigger: React.FC<React.PropsWithChildren> = ({ children }) => {
  return <>{children}</>
}
SelectTrigger.displayName = "SelectTrigger"

const SelectValue = React.forwardRef<
  HTMLOptionElement,
  React.OptionHTMLAttributes<HTMLOptionElement> & { placeholder?: string }
>(({ placeholder, children, ...props }, ref) => {
  return (
    <option ref={ref} value="" disabled hidden {...props}>
      {placeholder || children || "Select..."}
    </option>
  )
})
SelectValue.displayName = "SelectValue"

// SelectContent is a no-op wrapper for native select (children are options)
const SelectContent: React.FC<React.PropsWithChildren> = ({ children }) => {
  return <>{children}</>
}
SelectContent.displayName = "SelectContent"

const SelectItem = React.forwardRef<
  HTMLOptionElement,
  React.OptionHTMLAttributes<HTMLOptionElement>
>(({ className, children, ...props }, ref) => {
  return (
    <option ref={ref} className={cn("", className)} {...props}>
      {children}
    </option>
  )
})
SelectItem.displayName = "SelectItem"

export { Select, SelectTrigger, SelectValue, SelectContent, SelectItem }
