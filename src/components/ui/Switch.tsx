import React from 'react';
import { cn } from '../../lib/utils';

interface SwitchProps {
  id?: string;
  checked?: boolean;
  onChange?: (event: React.ChangeEvent<HTMLInputElement>) => void;
  disabled?: boolean;
  className?: string;
  name?: string;
}

export const Switch: React.FC<SwitchProps> = ({
  id,
  checked = false,
  onChange,
  disabled = false,
  className,
  name,
  ...props
}) => {
  return (
    <label
      htmlFor={id}
      className={cn(
        "relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-within:outline-none focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-2 focus-within:ring-offset-background",
        checked 
          ? "bg-primary" 
          : "bg-input",
        disabled 
          ? "opacity-50 cursor-not-allowed" 
          : "cursor-pointer",
        className
      )}
    >
      <input
        type="checkbox"
        id={id}
        name={name}
        checked={checked}
        onChange={onChange}
        disabled={disabled}
        className="sr-only"
        {...props}
      />
      <span
        className={cn(
          "inline-block h-4 w-4 transform rounded-full bg-background transition-transform",
          checked ? "translate-x-6" : "translate-x-1"
        )}
      />
    </label>
  );
}; 