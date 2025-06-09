import React from 'react';
import { cn } from '../../lib/utils';
import { Check } from 'lucide-react';

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, ...props }, ref) => {
    return (
      <div className="relative inline-flex items-center">
        <input
          type="checkbox"
          className="peer h-4 w-4 opacity-0 absolute"
          ref={ref}
          {...props}
        />
        <div
          className={cn(
            "h-5 w-5 rounded border border-input ring-offset-background peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2 peer-checked:border-primary peer-checked:bg-primary peer-checked:text-primary-foreground peer-disabled:cursor-not-allowed peer-disabled:opacity-50 flex items-center justify-center",
            className
          )}
        >
          <Check className="h-3.5 w-3.5 hidden peer-checked:[&+div>svg]:block" />
        </div>
      </div>
    );
  }
);

Checkbox.displayName = 'Checkbox';