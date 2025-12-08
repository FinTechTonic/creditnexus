import { ChevronRight, Home } from 'lucide-react';
import type { ReactNode } from 'react';

interface BreadcrumbItem {
  label: string;
  icon?: ReactNode;
  onClick?: () => void;
  href?: string;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  className?: string;
  onHomeClick?: () => void;
}

export function Breadcrumb({ items, className = '', onHomeClick }: BreadcrumbProps) {
  if (items.length === 0) return null;

  return (
    <nav aria-label="Breadcrumb" className={`flex items-center text-sm ${className}`}>
      <ol className="flex items-center gap-1">
        <li>
          <button
            onClick={() => {
              if (onHomeClick) onHomeClick();
            }}
            className="flex items-center gap-1 text-slate-400 hover:text-emerald-400 transition-colors"
            aria-label="Go to Dashboard"
          >
            <Home className="h-4 w-4" />
            <span className="sr-only">Home</span>
          </button>
        </li>
        {items.map((item, index) => (
          <li key={index} className="flex items-center gap-1">
            <ChevronRight className="h-4 w-4 text-slate-600" />
            {index === items.length - 1 ? (
              <span className="flex items-center gap-1.5 text-slate-200 font-medium">
                {item.icon}
                {item.label}
              </span>
            ) : (
              <a
                href={item.href || '#'}
                onClick={(e) => {
                  if (item.onClick) {
                    e.preventDefault();
                    item.onClick();
                  }
                }}
                className="flex items-center gap-1.5 text-slate-400 hover:text-emerald-400 transition-colors"
              >
                {item.icon}
                {item.label}
              </a>
            )}
          </li>
        ))}
      </ol>
    </nav>
  );
}

interface BreadcrumbContainerProps {
  children: ReactNode;
  className?: string;
}

export function BreadcrumbContainer({ children, className = '' }: BreadcrumbContainerProps) {
  return (
    <div className={`mb-6 ${className}`}>
      {children}
    </div>
  );
}
