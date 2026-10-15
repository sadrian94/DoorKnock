import React from 'react';
import { DoorOpen, Bookmark, Kanban, ChartNoAxesCombined, Plus, Settings } from 'lucide-react';

type Tab = 'dashboard' | 'saved' | 'kanban' | 'settings';

interface NavbarProps {
  currentTab: Tab;
  onTabChange: (tab: Tab) => void;
  savedCount: number;
  kanbanCount: number;
  onOpenImport: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentTab,
  onTabChange,
  savedCount,
  kanbanCount,
  onOpenImport,
}) => {
  return (
    <header className="sticky top-0 z-30 bg-ui-panel/90 backdrop-blur border-b border-ui-line-soft px-6 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="app-brand-mark h-10 w-10 rounded-xl bg-gradient-to-br from-ui-fill-amber-500 to-ui-fill-amber-700 flex items-center justify-center shadow-lg shadow-amber-900/30 border border-ui-line-amber-400/30">
            <DoorOpen className="h-5 w-5 text-ui-brand-mark" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-ui-heading flex items-center gap-1.5">
                DoorKnock
              </h1>
            </div>
            <p className="text-xs text-ui-muted">AI-assisted Job Hunting & Outreach Workflow</p>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex max-w-full items-center overflow-x-auto bg-ui-page p-1 rounded-xl border border-ui-line-soft shadow-inner">
          <button
            onClick={() => onTabChange('dashboard')}
            className={`flex shrink-0 items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'dashboard'
                ? 'bg-ui-fill-amber-600 text-ui-on-action shadow-md shadow-amber-950/50 font-semibold'
                : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-panel'
            }`}
          >
            <ChartNoAxesCombined className="h-4 w-4" />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => onTabChange('saved')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'saved'
                ? 'bg-ui-fill-amber-600 text-ui-on-action shadow-md shadow-amber-950/50 font-semibold'
                : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-panel'
            }`}
          >
            <Bookmark className="h-4 w-4" />
            <span>Saved Jobs</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              currentTab === 'saved' ? 'bg-ui-fill-amber-800/80 text-ui-ink-amber-100' : 'bg-ui-raised text-ui-muted'
            }`}>
              {savedCount}
            </span>
          </button>

          <button
            onClick={() => onTabChange('kanban')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'kanban'
                ? 'bg-ui-fill-amber-600 text-ui-on-action shadow-md shadow-amber-950/50 font-semibold'
                : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-panel'
            }`}
          >
            <Kanban className="h-4 w-4" />
            <span>Pipeline Kanban</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              currentTab === 'kanban' ? 'bg-ui-fill-amber-800/80 text-ui-ink-amber-100' : 'bg-ui-raised text-ui-muted'
            }`}>
              {kanbanCount}
            </span>
          </button>
          <button onClick={() => onTabChange('settings')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${currentTab === 'settings' ? 'bg-ui-fill-amber-600 text-ui-on-action' : 'text-ui-muted hover:text-ui-secondary hover:bg-ui-panel'}`}>
            <Settings className="h-4 w-4" /><span>Settings</span>
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenImport}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-ui-on-action bg-ui-fill-amber-600 hover:bg-ui-fill-amber-500 rounded-lg shadow-md shadow-amber-950/40 transition"
          >
            <Plus className="h-4 w-4" />
            <span>Import Job</span>
          </button>
        </div>
      </div>
    </header>
  );
};
