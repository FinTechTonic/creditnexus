import * as React from "react"
import { cn } from "@/lib/utils"

declare global {
  namespace JSX {
    interface IntrinsicElements {
      'model-viewer': React.DetailedHTMLProps<
        React.HTMLAttributes<HTMLElement> & {
          src?: string
          alt?: string
          'auto-rotate'?: boolean
          'camera-controls'?: boolean
        },
        HTMLElement
      >
    }
  }
}

interface ModelViewerProps {
  src: string
  className?: string
  alt?: string
  loading?: "auto" | "eager" | "lazy"
}

const ModelViewer = React.forwardRef<HTMLDivElement, ModelViewerProps>(
  ({ src, className, alt = "3D Model", loading = "auto" }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "relative w-full h-full rounded-lg overflow-hidden",
          "bg-[var(--color-model-bg)] border border-[var(--color-model-border)]",
          className
        )}
      >
        {/* eslint-disable-next-line @typescript-eslint/ban-ts-comment */}
        {React.createElement('model-viewer', {
          src,
          alt,
          loading,
          'auto-rotate': true,
          'camera-controls': true,
          className: "w-full h-full",
        }, React.createElement('div', { slot: 'progress-bar' }, 'Loading...'))}
      </div>
    )
  }
)
ModelViewer.displayName = "ModelViewer"

export { ModelViewer }
