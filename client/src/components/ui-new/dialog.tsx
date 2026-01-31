import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "./button"

/**
 * Dialog Component
 * Modal overlay with backdrop blur, focus trap, and keyboard support
 */
const dialogVariants = cva(
  "relative z-50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]",
  {
    variants: {
      size: {
        sm: "max-w-sm",
        md: "max-w-md",
        lg: "max-w-lg",
        xl: "max-w-xl",
        "2xl": "max-w-2xl",
        full: "max-w-full",
      },
    },
    defaultVariants: {
      size: "md",
    },
  }
)

export interface DialogProps {
  open: boolean
  onClose: () => void
  children: React.ReactNode
  size?: VariantProps<typeof dialogVariants>["size"]
  className?: string
}

const Dialog = React.forwardRef<HTMLDivElement, DialogProps>(
  ({ open, onClose, children, size, className }, forwardedRef) => {
    const dialogRef = React.useRef<HTMLDivElement>(null)
    
    React.useImperativeHandle(forwardedRef, () => dialogRef.current!)
    const [mounted, setMounted] = React.useState(false)

    React.useEffect(() => {
      setMounted(true)
      return () => setMounted(false)
    }, [])

    React.useEffect(() => {
      if (open) {
        document.body.style.overflow = "hidden"
        const firstFocusable = dialogRef.current?.querySelector(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        ) as HTMLElement | null
        firstFocusable?.focus()
      } else {
        document.body.style.overflow = ""
      }
      return () => {
        document.body.style.overflow = ""
      }
    }, [open])

    React.useEffect(() => {
      const handleKeyDown = (e: KeyboardEvent) => {
        if (!open) return
        if (e.key === "Escape") {
          onClose()
        }
        if (e.key === "Tab" && dialogRef.current) {
          const focusableElements = dialogRef.current.querySelectorAll(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
          const firstElement = focusableElements[0] as HTMLElement
          const lastElement = focusableElements[focusableElements.length - 1] as HTMLElement
          if (e.shiftKey && document.activeElement === firstElement) {
            e.preventDefault()
            lastElement.focus()
          } else if (!e.shiftKey && document.activeElement === lastElement) {
            e.preventDefault()
            firstElement.focus()
          }
        }
      }
      document.addEventListener("keydown", handleKeyDown)
      return () => document.removeEventListener("keydown", handleKeyDown)
    }, [open, onClose])

    if (!mounted || !open) return null

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center">
        <div
          className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
          onClick={onClose}
          aria-hidden="true"
        />
        <div
          ref={dialogRef}
          className={cn(
            dialogVariants({ size, className }),
            "w-full mx-4 bg-slate-800/95 border border-slate-700 shadow-2xl rounded-xl overflow-hidden"
          )}
          role="dialog"
          aria-modal="true"
        >
          {children}
        </div>
      </div>
    )
  }
)
Dialog.displayName = "Dialog"

const DialogHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex flex-col space-y-1.5 p-6 border-b border-slate-700/50",
      className
    )}
    {...props}
  />
))
DialogHeader.displayName = "DialogHeader"

const DialogTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h2
    ref={ref}
    className={cn(
      "text-xl font-semibold leading-none tracking-tight text-slate-100",
      className
    )}
    {...props}
  />
))
DialogTitle.displayName = "DialogTitle"

const DialogDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-slate-400", className)}
    {...props}
  />
))
DialogDescription.displayName = "DialogDescription"

const DialogContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("p-6", className)}
    {...props}
  />
))
DialogContent.displayName = "DialogContent"

const DialogFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "flex items-center justify-end gap-3 p-6 border-t border-slate-700/50",
      className
    )}
    {...props}
  />
))
DialogFooter.displayName = "DialogFooter"

const DialogCloseButton = React.forwardRef<
  HTMLButtonElement,
  React.ButtonHTMLAttributes<HTMLButtonElement> & { onClose?: () => void }
>(({ onClose, className, ...props }, ref) => (
  <button
    ref={ref}
    onClick={onClose}
    className={cn(
      "absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:ring-offset-2 disabled:pointer-events-none",
      className
    )}
    {...props}
  >
    <svg
      className="h-5 w-5 text-slate-400 hover:text-slate-200"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M6 18L18 6M6 6l12 12"
      />
    </svg>
    <span className="sr-only">Close</span>
  </button>
))
DialogCloseButton.displayName = "DialogCloseButton"

export {
  Dialog,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogContent,
  DialogFooter,
  DialogCloseButton,
  dialogVariants,
}
