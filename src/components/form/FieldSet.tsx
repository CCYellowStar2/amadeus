import React from 'react';
import { cn } from '../../lib/utils';

interface FieldSetProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  className?: string;
}

export const FieldSet: React.FC<FieldSetProps> = ({
  title,
  description,
  children,
  className,
}) => {
  return (
    <fieldset className={cn("space-y-6", className)}>
      {(title || description) && (
        <div className="space-y-1 mb-4">
          {title && (
            <h3 className="text-lg font-medium">{title}</h3>
          )}
          {description && (
            <p className="text-sm text-muted-foreground">{description}</p>
          )}
        </div>
      )}
      <div className="space-y-4">
        {children}
      </div>
    </fieldset>
  );
};