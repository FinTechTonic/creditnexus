import * as React from "react"
// cn removed - unused

export interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  children: React.ReactNode
}

export function CommandPalette({ open, onOpenChange, children }: CommandPaletteProps) {
  React.useEffect(() => {
    if (!open) return
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onOpenChange(false)
      }
    }
    
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [open, onOpenChange])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div 
        className="fixed inset-0 bg-[var(--color-overlay)] backdrop-blur-sm"
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />
      <div className="relative z-50 w-full max-w-xl">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-panel)] shadow-lg overflow-hidden">
          {children}
        </div>
      </div>
    </div>
  )
}

// CommandPalette already exported above
