import * as React from "react"
import { cn } from "@/lib/utils"

export interface TimelineItem {
  title: string
  description?: string
  date: string
  icon?: React.ReactNode
}

export interface TimelineProps {
  items: TimelineItem[]
  className?: string
}

export function Timeline({ items, className }: TimelineProps) {
  return (
    <div className={cn("space-y-8", className)}>
      {items.map((item, index) => (
        <div key={index} className="relative flex gap-4">
          <div className="flex flex-col items-center">
            <div className="h-4 w-4 rounded-full bg-[var(--color-timeline-dot)] border-2 border-[var(--color-timeline-dot-border)]" />
            {index !== items.length - 1 && (
              <div className="w-0.5 h-full bg-[var(--color-timeline-line)] mt-2" />
            )}
          </div>
          <div className="flex-1">
            <div className="text-sm text-[var(--color-timeline-date)]">{item.date}</div>
            <h3 className="text-base font-medium text-[var(--color-timeline-title)]">{item.title}</h3>
            {item.description && (
              <p className="text-sm text-[var(--color-timeline-description)] mt-1">{item.description}</p>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// Timeline already exported above
