import React, { useState, useEffect } from 'react';
import { Search, MapPin, Building2, Clock, ExternalLink, ChevronLeft, ChevronRight, Eye, EyeOff } from 'lucide-react';
import type { KanbanCard } from '../types';
import { sortCards, type CardSort } from '../sortCards';
import { useTimeSettings } from '../timeSettings';
import { daysAgo, hasUnknownTimeZone } from '../time';

interface KanbanBoardProps {
  stages: Record<string, KanbanCard[]>;
  onSelectJob: (jobId: string) => void;
  isLoading: boolean;
}

interface StageMeta {
  key: string;
  label: string;
  badgeColor: string;
  borderColor: string;
}

const STAGES_CONFIG: StageMeta[] = [
  { key: 'saved', label: 'Saved', badgeColor: 'bg-ui-raised text-ui-body', borderColor: 'border-ui-line' },
  { key: 'applied', label: 'Applied', badgeColor: 'bg-ui-fill-blue-950 text-ui-ink-blue-300', borderColor: 'border-ui-line-blue-800/60' },
  { key: 'knocked', label: 'Contacted', badgeColor: 'bg-ui-fill-amber-950 text-ui-ink-amber-300', borderColor: 'border-ui-line-amber-800/60' },
  { key: 'recruiter_screen', label: 'Recruiter Screen', badgeColor: 'bg-ui-fill-purple-950 text-ui-ink-purple-300', borderColor: 'border-ui-line-purple-800/60' },
  { key: 'assessment', label: 'Assessment', badgeColor: 'bg-ui-fill-indigo-950 text-ui-ink-indigo-300', borderColor: 'border-ui-line-indigo-800/60' },
  { key: 'team_match', label: 'Team Match', badgeColor: 'bg-ui-fill-cyan-950 text-ui-ink-cyan-300', borderColor: 'border-ui-line-cyan-800/60' },
  { key: 'technical_interview', label: 'Tech Interview', badgeColor: 'bg-ui-fill-teal-950 text-ui-ink-teal-300', borderColor: 'border-ui-line-teal-800/60' },
  { key: 'final_round', label: 'Final Round', badgeColor: 'bg-ui-fill-orange-950 text-ui-ink-orange-300', borderColor: 'border-ui-line-orange-800/60' },
  { key: 'offer', label: 'Offer 🎉', badgeColor: 'bg-ui-fill-emerald-950 text-ui-ink-emerald-300', borderColor: 'border-ui-line-emerald-700/80' },
  { key: 'closed', label: 'Closed', badgeColor: 'bg-ui-fill-red-950/60 text-ui-ink-red-400', borderColor: 'border-ui-line-red-900/60' },
];

const DEFAULT_COLLAPSED: Record<string, boolean> = {
  saved: true,
  closed: true,
};

const getInitialCollapsedStages = (): Record<string, boolean> => {
  try {
    const saved = localStorage.getItem('doorknock_kanban_collapsed_stages');
    if (saved) return JSON.parse(saved);
  } catch {
    // fallback
  }
  return DEFAULT_COLLAPSED;
};

const getInitialHideEmpty = (): boolean => {
  try {
    const saved = localStorage.getItem('doorknock_kanban_hide_empty');
    if (saved !== null) return saved === 'true';
  } catch {
    // fallback
  }
  return true;
};

export const KanbanBoard: React.FC<KanbanBoardProps> = ({
  stages,
  onSelectJob,
  isLoading,
}) => {
  const { settings } = useTimeSettings();
  const [searchTerm, setSearchTerm] = useState('');
  const [sortOrder, setSortOrder] = useState<CardSort>('newest');
  const [collapsedStages, setCollapsedStages] = useState<Record<string, boolean>>(getInitialCollapsedStages);
  const [hideEmptyStages, setHideEmptyStages] = useState<boolean>(getInitialHideEmpty);

  useEffect(() => {
    try {
      localStorage.setItem('doorknock_kanban_collapsed_stages', JSON.stringify(collapsedStages));
    } catch {
      // ignore
    }
  }, [collapsedStages]);

  useEffect(() => {
    try {
      localStorage.setItem('doorknock_kanban_hide_empty', String(hideEmptyStages));
    } catch {
      // ignore
    }
  }, [hideEmptyStages]);

  const toggleStageCollapsed = (stageKey: string) => {
    setCollapsedStages((prev) => ({
      ...prev,
      [stageKey]: !prev[stageKey],
    }));
  };

  const filterCards = (cards: KanbanCard[] = []) => {
    if (!searchTerm) return cards;
    return cards.filter(
      (c) =>
        c.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        c.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (c.location && c.location.toLowerCase().includes(searchTerm.toLowerCase()))
    );
  };

  const getDaysAgo = (dateStr?: string) => {
    return daysAgo(dateStr, settings.timezone);
  };

  const emptyStagesCount = STAGES_CONFIG.filter((col) => {
    const rawCards = stages[col.key] || [];
    return rawCards.length === 0;
  }).length;

  return (
    <div className="flex flex-col h-[calc(100vh-65px)]">
      {/* Top Toolbar */}
      <div className="px-6 py-4 border-b border-ui-line-soft bg-ui-panel/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-ui-heading tracking-tight">Application Pipeline</h2>
          <p className="text-xs text-ui-muted">
            Track stage progression, outreach touchpoints, and interview milestones.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setHideEmptyStages(!hideEmptyStages)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl border transition-all ${
              hideEmptyStages
                ? 'bg-ui-fill-amber-950/40 text-ui-ink-amber-300 border-ui-line-amber-800/60 hover:bg-ui-fill-amber-950/60'
                : 'bg-ui-panel text-ui-muted border-ui-line-soft hover:text-ui-secondary hover:bg-ui-raised'
            }`}
            title={hideEmptyStages ? 'Showing only active stages. Click to show all empty stages.' : 'Click to hide stages with 0 applications.'}
          >
            {hideEmptyStages ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
            <span>
              {hideEmptyStages
                ? `Hide Empty (${emptyStagesCount})`
                : 'Show All Stages'}
            </span>
          </button>

          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-ui-muted" />
            <input
              type="text"
              placeholder="Search applications..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-ui-panel border border-ui-line text-ui-secondary text-xs rounded-xl pl-9 pr-4 py-1.5 w-60 focus:outline-none focus:border-ui-line-amber-500 shadow-sm"
            />
          </div>
          <select
            aria-label="Sort applications within stages"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as CardSort)}
            className="bg-ui-panel border border-ui-line text-ui-secondary text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-ui-line-amber-500"
          >
            <option value="newest">Recently updated</option>
            <option value="oldest">Oldest updated</option>
            <option value="company-asc">Company A–Z</option>
            <option value="company-desc">Company Z–A</option>
            <option value="score-desc">Match score: high to low</option>
            <option value="score-asc">Match score: low to high</option>
          </select>
        </div>
      </div>

      {/* Columns Container */}
      <div className="flex-1 overflow-x-auto p-6 bg-ui-page">
        {isLoading ? (
          <div className="flex items-center justify-center h-64 text-ui-muted">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ui-line-amber-500"></div>
          </div>
        ) : (
          <div className="flex gap-4 items-start min-w-max pb-4">
            {STAGES_CONFIG.map((col) => {
              const rawCards = stages[col.key] || [];
              const cards = sortCards(filterCards(rawCards), sortOrder, 'updated_at');

              // If hiding empty stages and this column has 0 raw cards, omit it
              if (hideEmptyStages && rawCards.length === 0) {
                return null;
              }

              const isCollapsed = Boolean(collapsedStages[col.key]);

              if (isCollapsed) {
                return (
                  <div
                    key={col.key}
                    onClick={() => toggleStageCollapsed(col.key)}
                    className="w-12 flex-shrink-0 bg-ui-panel/60 hover:bg-ui-panel border border-ui-line-soft/80 hover:border-ui-line rounded-2xl flex flex-col items-center py-4 cursor-pointer transition-all max-h-[calc(100vh-170px)] select-none group shadow-sm"
                    title={`Click to expand ${col.label} (${cards.length} cards)`}
                  >
                    <button
                      type="button"
                      className="p-1 rounded-lg text-ui-muted group-hover:text-ui-ink-amber-400 group-hover:bg-ui-raised transition mb-3"
                      aria-label={`Expand ${col.label}`}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>

                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold mb-4 ${col.badgeColor}`}>
                      {cards.length}
                    </span>

                    <div className="flex-1 flex items-center justify-center">
                      <span className="text-xs font-semibold text-ui-muted group-hover:text-ui-secondary tracking-wider [writing-mode:vertical-lr] rotate-180 transition whitespace-nowrap">
                        {col.label}
                      </span>
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={col.key}
                  className={`w-72 flex-shrink-0 bg-ui-panel/70 border ${col.borderColor} rounded-2xl flex flex-col max-h-[calc(100vh-170px)]`}
                >
                  {/* Column Header */}
                  <div className="p-3.5 border-b border-ui-line-soft/80 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-ui-secondary">{col.label}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${col.badgeColor}`}>
                        {cards.length}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleStageCollapsed(col.key)}
                      className="p-1 rounded-lg text-ui-subtle hover:text-ui-secondary hover:bg-ui-raised transition"
                      title={`Collapse ${col.label} column`}
                      aria-label={`Collapse ${col.label}`}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Card List */}
                  <div className="p-3 overflow-y-auto space-y-3 flex-1">
                    {cards.length === 0 ? (
                      <div className="py-8 text-center text-xs text-ui-faint border border-dashed border-ui-line-soft rounded-xl">
                        No applications
                      </div>
                    ) : (
                      cards.map((card) => {
                        const daysAgo = getDaysAgo(card.applied_date || card.updated_at);
                        const isOutcomeRejected = card.current_stage === 'closed' && card.outcome === 'rejected';
                        const isOutcomeOffer = (card.current_stage === 'closed' || card.current_stage === 'offer') && card.outcome === 'offer_accepted';

                        return (
                          <div
                            key={card.application_id}
                            className={`group relative bg-ui-page/80 border rounded-xl p-3.5 hover:shadow-lg hover:border-ui-line-strong transition flex flex-col justify-between ${
                              isOutcomeRejected
                                ? 'border-ui-line-red-950/80 opacity-75'
                                : isOutcomeOffer
                                ? 'border-ui-line-emerald-700/80'
                                : 'border-ui-line-soft'
                            }`}
                          >
                            {/* Card Top: Company & Days */}
                            <div>
                              <div className="flex items-start justify-between gap-2 mb-1.5">
                                <div className="flex items-center gap-1.5 text-xs font-semibold text-ui-body truncate">
                                  <Building2 className="h-3.5 w-3.5 text-ui-muted flex-shrink-0" />
                                  <span className="truncate">{card.company}</span>
                                </div>

                                {card.outcome && <span className="text-[10px] text-ui-muted">{card.outcome.replaceAll('_', ' ')}</span>}

                              </div>

                              {/* Title */}
                              <h4
                                onClick={() => onSelectJob(card.job_id)}
                                className="text-xs font-bold text-ui-heading group-hover:text-ui-ink-amber-400 transition cursor-pointer line-clamp-2"
                              >
                                {card.title}
                              </h4>

                              {/* Tags */}
                              <div className="flex flex-wrap items-center gap-2 mt-2 text-[11px] text-ui-muted">
                                {card.location && (
                                  <span className="flex items-center gap-1 text-ui-muted truncate max-w-[150px]">
                                    <MapPin className="h-3 w-3 text-ui-subtle" />
                                    <span className="truncate">{card.location}</span>
                                  </span>
                                )}
                              </div>

                              {/* Timeline indicator & Touchpoints */}
                              {card.next_action && card.next_action.state !== 'closed' && (
                                <p className="mt-2 text-[10px] text-ui-ink-amber-300">{card.next_action.state === 'waiting' ? 'Waiting for response' : card.next_action.label}</p>
                              )}
                              <div className="flex items-center justify-between text-[10px] text-ui-subtle mt-3 pt-2 border-t border-ui-line-soft/80">
                                {daysAgo && (
                                  <span className="flex items-center gap-1 text-ui-muted"
                                    title={hasUnknownTimeZone(card.applied_date || card.updated_at || '') ? 'Original date; time zone not recorded' : settings.timezone}>
                                    <Clock className="h-3 w-3" />
                                    {daysAgo}
                                  </span>
                                )}

                                <div className="flex items-center gap-2">
                                  {(() => {
                                    let decision: string | null = null;
                                    if (card.analysis_json) {
                                      try {
                                        const parsed = typeof card.analysis_json === 'string' ? JSON.parse(card.analysis_json) : card.analysis_json;
                                        decision = parsed?.triage?.decision || null;
                                      } catch {
                                        // ignore
                                      }
                                    }
                                    if (!decision && card.suitability_score !== undefined && card.suitability_score !== null) {
                                      const s = card.suitability_score;
                                      if (s >= 90) decision = 'STRONG_KNOCK';
                                      else if (s >= 75) decision = 'SELECTIVE_APPLY';
                                      else if (s >= 60) decision = 'HIGH_RISK_LOW_ROI';
                                      else decision = 'HARD_PASS';
                                    }
                                    if (!decision) return null;

                                    const badge = {
                                      STRONG_KNOCK: { label: 'STRONG', icon: '🎯', style: 'text-ui-ink-emerald-400 bg-ui-fill-emerald-950/80 border-ui-line-emerald-800/70' },
                                      SELECTIVE_APPLY: { label: 'SELECTIVE', icon: '⚡', style: 'text-ui-ink-amber-400 bg-ui-fill-amber-950/80 border-ui-line-amber-800/70' },
                                      HIGH_RISK_LOW_ROI: { label: 'HIGH RISK', icon: '⚠️', style: 'text-ui-ink-rose-400 bg-ui-fill-rose-950/80 border-ui-line-rose-800/70' },
                                      HARD_PASS: { label: 'PASS', icon: '⛔', style: 'text-ui-muted bg-ui-panel border-ui-line' },
                                      DO_NOT_APPLY: { label: 'PASS', icon: '⛔', style: 'text-ui-muted bg-ui-panel border-ui-line' },
                                    }[decision] || { label: decision.replace(/_/g, ' '), icon: '📋', style: 'text-ui-muted bg-ui-raised border-ui-line' };

                                    return (
                                      <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border flex items-center gap-1 shadow-sm ${badge.style}`} title={`Triage Verdict: ${decision.replace(/_/g, ' ')}`}>
                                        <span>{badge.icon}</span>
                                        <span>{badge.label}</span>
                                      </span>
                                    );
                                  })()}
                                  {card.job_url && (
                                    <a
                                      href={card.job_url}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="text-ui-muted hover:text-ui-heading"
                                      title="Open link"
                                    >
                                      <ExternalLink className="h-3 w-3" />
                                    </a>
                                  )}
                                </div>
                              </div>
                            </div>

                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
