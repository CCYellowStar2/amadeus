import React from 'react';
import * as Icons from 'lucide-react';
import { cn } from '../lib/utils';

interface EmptyStateProps {
  title: string;
  description: string;
  icon: string;
  isSpinning?: boolean;
}

const EmptyState: React.FC<EmptyStateProps> = ({ title, description, icon, isSpinning = false }) => {
  // Dynamically get icon component
  const IconComponent = (Icons as any)[icon] || Icons.HelpCircle;

  return (
    <div className="text-center p-8 bg-card h-full flex flex-col items-center justify-center">
      <div className="flex items-center justify-center w-16 h-16 rounded-full bg-muted mb-4">
        <IconComponent className={cn("h-8 w-8 text-muted-foreground", { 'animate-spin': isSpinning })} />
      </div>
      <h3 className="text-lg font-semibold mb-1">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
};

export default EmptyState;