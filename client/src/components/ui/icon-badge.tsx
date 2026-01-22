import * as React from "react"
import { cn } from "@/lib/utils"

interface IconBadgeProps {
  icon: React.ReactNode
  variant?: "default" | "primary" | "success" | "warning" | "error"
  size?: "sm" | "md" | "lg"
  className?: string
}

const IconBadge = React.forwardRef<HTMLDivElement, IconBadgeProps>(
  ({ icon, variant = "default", size = "md", className }, ref) => {
    const variantClasses = {
      default: "bg-[var(--color-icon-bg)] text-[var(--color-icon)]",
      primary: "bg-[var(--color-icon-primary-bg)] text-[var(--color-icon-primary)]",
      success: "bg-[var(--color-icon-success-bg)] text-[var(--color-icon-success)]",
      warning: "bg-[var(--color-icon-warning-bg)] text-[var(--color-icon-warning)]",
      error: "bg-[var(--color-icon-error-bg)] text-[var(--color-icon-error)]"
    }

    const sizeClasses = {
      sm: "h-8 w-8",
      md: "h-10 w-10",
      lg: "h-12 w-12"
    }

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-full flex items-center justify-center",
          variantClasses[variant],
          sizeClasses[size],
          className
        )}
      >
        {React.isValidElement(icon) && React.cloneElement(icon as React.ReactElement<any>, {
          className: cn(
            size === "sm" && "h-4 w-4",
            size === "md" && "h-5 w-5",
            size === "lg" && "h-6 w-6",
            (icon.props as any)?.className
          )
        })}
      </div>
    )
  }
)
IconBadge.displayName = "IconBadge"

export { IconBadge }
