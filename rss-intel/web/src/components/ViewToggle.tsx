'use client';

import { LayoutGrid, List } from 'lucide-react';
import { Toggle } from '@/components/ui/toggle';
import { cn } from '@/lib/utils';

export type ViewMode = 'list' | 'cards';

interface ViewToggleProps {
  view: ViewMode;
  onViewChange: (view: ViewMode) => void;
  className?: string;
}

export function ViewToggle({ view, onViewChange, className }: ViewToggleProps) {
  return (
    <div className={cn("flex rounded-lg border p-1", className)}>
      <Toggle
        pressed={view === 'list'}
        onPressedChange={() => onViewChange('list')}
        className="rounded-md px-3 py-1.5"
        size="sm"
      >
        <List className="h-4 w-4" />
        <span className="ml-2 text-sm">List</span>
      </Toggle>
      <Toggle
        pressed={view === 'cards'}
        onPressedChange={() => onViewChange('cards')}
        className="rounded-md px-3 py-1.5"
        size="sm"
      >
        <LayoutGrid className="h-4 w-4" />
        <span className="ml-2 text-sm">Cards</span>
      </Toggle>
    </div>
  );
}