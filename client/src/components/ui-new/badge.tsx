import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "./button"

/**
 * Badge Component Variants
 * Default, Primary, Success, Warning, Error, Info variants
 */
const badgeVariants = cva(
  "inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-full font-medium transition-all duration-200",
  {
    variants: {
      variant: {
        default:
          "bg-slate-700 text-slate-200 hover:bg-slate-600",
        primary:
          "bg-[#3B82F6]/20 text-[#3B82F6] hover:bg-[#3B82F6]/30 border border-[#3B82F6]/30",
        success:
          "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30",
        warning:
          "bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 border border-amber-500/30",
        error:
          "bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30",
        info:
          "bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 border border-cyan-500/30",
      },
      size: {
        sm: "px-2 py-0.5 text-xs",
        md: "px-3 py-1 text-sm",
        lg: "px-4 py-1.5 text-base",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "md",
    },
  }
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  icon?: React.ReactNode
}

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant, size, icon, children, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(badgeVariants({ variant, size, className }))}
      {...props}
    >
      {icon && <span className="flex-shrink-0">{icon}</span>}
      {children}
    </span>
  )
)
Badge.displayName = "Badge"

export { Badge, badgeVariants }
