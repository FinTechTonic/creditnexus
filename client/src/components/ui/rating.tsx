// React import removed - unused (using JSX transform)
import { cn } from "@/lib/utils"

export interface RatingProps {
  value: number
  max?: number
  onChange?: (value: number) => void
  className?: string
  readOnly?: boolean
}

export function Rating({ 
  value, 
  max = 5, 
  onChange, 
  className, 
  readOnly = false 
}: RatingProps) {
  return (
    <div className={cn("flex items-center", className)}>
      {[...Array(max)].map((_, i) => (
        <button
          key={i}
          type="button"
          onClick={() => !readOnly && onChange?.(i + 1)}
          className={cn(
            "text-2xl transition-colors",
            i < value ? "text-[var(--color-rating-active)]" : "text-[var(--color-rating-inactive)]",
            !readOnly && "hover:text-[var(--color-rating-hover)]"
          )}
          disabled={readOnly}
          aria-label={`Rate ${i + 1} out of ${max}`}
        >
          ★
        </button>
      ))}
    </div>
  )
}

// Rating already exported above
