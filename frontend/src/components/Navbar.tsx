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
    <header className="sticky top-0 z-30 bg-slate-900/90 backdrop-blur border-b border-slate-800 px-6 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center shadow-lg shadow-amber-900/30 border border-amber-400/30">
            <DoorOpen className="h-5 w-5 text-amber-50" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
                DoorKnock
              </h1>
            </div>
            <p className="text-xs text-slate-400">AI-assisted Job Hunting & Outreach Workflow</p>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <div className="flex items-center overflow-x-auto bg-slate-950 p-1 rounded-xl border border-slate-800 shadow-inner">
          <button
            onClick={() => onTabChange('dashboard')}
            className={`flex shrink-0 items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'dashboard'
                ? 'bg-amber-600 text-white shadow-md shadow-amber-950/50 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <ChartNoAxesCombined className="h-4 w-4" />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => onTabChange('saved')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'saved'
                ? 'bg-amber-600 text-white shadow-md shadow-amber-950/50 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Bookmark className="h-4 w-4" />
            <span>Saved Jobs</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              currentTab === 'saved' ? 'bg-amber-800/80 text-amber-100' : 'bg-slate-800 text-slate-400'
            }`}>
              {savedCount}
            </span>
          </button>

          <button
            onClick={() => onTabChange('kanban')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              currentTab === 'kanban'
                ? 'bg-amber-600 text-white shadow-md shadow-amber-950/50 font-semibold'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
            }`}
          >
            <Kanban className="h-4 w-4" />
            <span>Pipeline Kanban</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              currentTab === 'kanban' ? 'bg-amber-800/80 text-amber-100' : 'bg-slate-800 text-slate-400'
            }`}>
              {kanbanCount}
            </span>
          </button>
          <button onClick={() => onTabChange('settings')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${currentTab === 'settings' ? 'bg-amber-600 text-white' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'}`}>
            <Settings className="h-4 w-4" /><span>Settings</span>
          </button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-3">
          <button
            onClick={onOpenImport}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-amber-600 hover:bg-amber-500 rounded-lg shadow-md shadow-amber-950/40 transition"
          >
            <Plus className="h-4 w-4" />
            <span>Import Job</span>
          </button>
        </div>
      </div>
    </header>
  );
};
