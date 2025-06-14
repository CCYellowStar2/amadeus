import React from 'react';
import { cn } from '../../lib/utils';
import { Loader2 } from 'lucide-react';

interface SwitchProps {
  id?: string;
  checked?: boolean;
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  className?: string;
  name?: string;
  isLoading?: boolean;
}

export const Switch: React.FC<SwitchProps> = ({
  id,
  checked = false,
  onChange,
  disabled = false,
  className,
  name,
  isLoading = false,
  ...props
}) => {
  const isEffectivelyDisabled = disabled || (isLoading && checked);

  return (
    <label
      htmlFor={id}
      className={cn(
        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background",
        checked ? "bg-primary" : "bg-input",
        isEffectivelyDisabled ? "cursor-not-allowed opacity-50" : "cursor-pointer",
        className
      )}
    >
      <input
        type="checkbox"
        id={id}
        name={name}
        checked={checked}
        onChange={onChange}
        disabled={isEffectivelyDisabled}
        className="sr-only"
        {...props}
      />
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-background transition-transform",
          checked ? "translate-x-6" : "translate-x-1",
          isLoading && checked ? 'opacity-0' : 'opacity-100'
        )}
      />
      {isLoading && checked && (
        <span
          className="absolute flex h-4 w-4 items-center justify-center transform translate-x-6"
        >
          <Loader2 className="h-4 w-4 animate-spin text-primary-foreground" />
        </span>
      )}
    </label>
  );
}; 