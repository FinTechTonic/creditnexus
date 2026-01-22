import * as React from "react"
import { cn } from "@/lib/utils"

export interface CarouselProps {
  children: React.ReactNode
  className?: string
}

export function Carousel({ children, className }: CarouselProps) {
  const [currentIndex, setCurrentIndex] = React.useState(0)
  
  const goNext = () => {
    setCurrentIndex(prev => (prev + 1) % React.Children.count(children))
  }
  
  const goPrev = () => {
    setCurrentIndex(prev => (prev - 1 + React.Children.count(children)) % React.Children.count(children))
  }

  return (
    <div className={cn("relative overflow-hidden", className)}>
      <div 
        className="flex transition-transform duration-300"
        style={{ transform: `translateX(-${currentIndex * 100}%)` }}
      >
        {React.Children.map(children, (child, i) => (
          <div key={i} className="w-full flex-shrink-0">
            {child}
          </div>
        ))}
      </div>
      
      <button 
        onClick={goPrev}
        className="absolute left-2 top-1/2 -translate-y-1/2 bg-[var(--color-carousel-control)] rounded-full p-2"
        aria-label="Previous slide"
      >
        ←
      </button>
      
      <button 
        onClick={goNext}
        className="absolute right-2 top-1/2 -translate-y-1/2 bg-[var(--color-carousel-control)] rounded-full p-2"
        aria-label="Next slide"
      >
        →
      </button>
    </div>
  )
}

// Carousel already exported above
