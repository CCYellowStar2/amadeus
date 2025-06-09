import React from 'react';
import { cn } from '../../lib/utils';
import { X } from 'lucide-react';

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'outline';
  onRemove?: () => void;
}

export const Badge = React.forwardRef<HTMLDivElement, BadgeProps>(
  ({ className, variant = 'default', onRemove, children, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
          {
            "bg-accent text-accent-foreground hover:bg-accent/80": variant === 'default',
            "bg-muted text-muted-foreground hover:bg-muted/80": variant === 'secondary',
            "border border-input bg-background hover:bg-accent hover:text-accent-foreground": variant === 'outline',
          },
          className
        )}
        {...props}
      >
        {children}
        {onRemove && (
          <button
            type="button"
            onClick={onRemove}
            className="ml-1 rounded-full outline-none ring-offset-background focus:ring-2 focus:ring-ring focus:ring-offset-2"
          >
            <X className="h-3 w-3" />
            <span className="sr-only">Remove</span>
          </button>
        )}
      </div>
    );
  }
);

Badge.displayName = 'Badge'; 