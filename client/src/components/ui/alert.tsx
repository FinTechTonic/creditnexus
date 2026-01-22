import * as React from "react"
import { cn } from "@/lib/utils"

interface AlertProps {
  variant?: "default" | "success" | "warning" | "error" | "destructive" 
  title?: string
  className?: string
  children: React.ReactNode
}

const Alert = React.forwardRef<HTMLDivElement, AlertProps>(
  ({ variant = "default", title, className, children }, ref) => {
    const variantClasses: Record<string, string> = {
      default: "bg-[var(--color-alert-bg)] border-[var(--color-alert-border)]",
      success: "bg-[var(--color-alert-success-bg)] border-[var(--color-alert-success-border)]",
      warning: "bg-[var(--color-alert-warning-bg)] border-[var(--color-alert-warning-border)]", 
      error: "bg-[var(--color-alert-error-bg)] border-[var(--color-alert-error-border)]",
      destructive: "bg-[var(--color-alert-error-bg)] border-[var(--color-alert-error-border)]"
    }

    return (
      <div
        ref={ref}
        className={cn(
          "rounded-lg border p-4 shadow-sm",
          variantClasses[variant] || variantClasses.default,
          className
        )}
      >
        {title && <h3 className="font-medium mb-2">{title}</h3>}
        <div className="text-sm">{children}</div>
      </div>
    )
  }
)
Alert.displayName = "Alert"

const AlertTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h5
    ref={ref}
    className={cn("mb-1 font-medium leading-none tracking-tight", className)}
    {...props}
  />
))
AlertTitle.displayName = "AlertTitle"

const AlertDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("text-sm [&_p]:leading-relaxed", className)}
    {...props}
  />
))
AlertDescription.displayName = "AlertDescription"

export { Alert, AlertTitle, AlertDescription }
