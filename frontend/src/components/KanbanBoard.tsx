import React, { useState, useEffect } from 'react';
import { Search, MapPin, Building2, Clock, ExternalLink, ChevronLeft, ChevronRight, Eye, EyeOff } from 'lucide-react';
import type { KanbanCard } from '../types';
import { sortCards, type CardSort } from '../sortCards';

interface KanbanBoardProps {
  stages: Record<string, KanbanCard[]>;
  onSelectJob: (jobId: string) => void;
  onMoveStage: (applicationId: string, toStage: string, outcome?: string) => void;
  isLoading: boolean;
}

interface StageMeta {
  key: string;
  label: string;
  badgeColor: string;
  borderColor: string;
}

const STAGES_CONFIG: StageMeta[] = [
  { key: 'saved', label: 'Saved', badgeColor: 'bg-slate-800 text-slate-300', borderColor: 'border-slate-700' },
  { key: 'applied', label: 'Applied', badgeColor: 'bg-blue-950 text-blue-300', borderColor: 'border-blue-800/60' },
  { key: 'knocked', label: 'Knocked', badgeColor: 'bg-amber-950 text-amber-300', borderColor: 'border-amber-800/60' },
  { key: 'recruiter_screen', label: 'Recruiter Screen', badgeColor: 'bg-purple-950 text-purple-300', borderColor: 'border-purple-800/60' },
  { key: 'assessment', label: 'Assessment', badgeColor: 'bg-indigo-950 text-indigo-300', borderColor: 'border-indigo-800/60' },
  { key: 'team_match', label: 'Team Match', badgeColor: 'bg-cyan-950 text-cyan-300', borderColor: 'border-cyan-800/60' },
  { key: 'technical_interview', label: 'Tech Interview', badgeColor: 'bg-teal-950 text-teal-300', borderColor: 'border-teal-800/60' },
  { key: 'final_round', label: 'Final Round', badgeColor: 'bg-orange-950 text-orange-300', borderColor: 'border-orange-800/60' },
  { key: 'offer', label: 'Offer 🎉', badgeColor: 'bg-emerald-950 text-emerald-300', borderColor: 'border-emerald-700/80' },
  { key: 'closed', label: 'Closed', badgeColor: 'bg-red-950/60 text-red-400', borderColor: 'border-red-900/60' },
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
  onMoveStage,
  isLoading,
}) => {
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
    if (!dateStr) return null;
    const diff = Math.floor((Date.now() - new Date(dateStr).getTime()) / (1000 * 60 * 60 * 24));
    if (diff <= 0) return 'Today';
    return `${diff}d ago`;
  };

  const emptyStagesCount = STAGES_CONFIG.filter((col) => {
    const rawCards = stages[col.key] || [];
    return rawCards.length === 0;
  }).length;

  return (
    <div className="flex flex-col h-[calc(100vh-65px)]">
      {/* Top Toolbar */}
      <div className="px-6 py-4 border-b border-slate-800 bg-slate-900/50 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight">Application Pipeline</h2>
          <p className="text-xs text-slate-400">
            Track stage progression, outreach touchpoints, and interview milestones.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setHideEmptyStages(!hideEmptyStages)}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-xl border transition-all ${
              hideEmptyStages
                ? 'bg-amber-950/40 text-amber-300 border-amber-800/60 hover:bg-amber-950/60'
                : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-slate-200 hover:bg-slate-800'
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
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Search applications..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-xl pl-9 pr-4 py-1.5 w-60 focus:outline-none focus:border-amber-500 shadow-sm"
            />
          </div>
          <select
            aria-label="Sort applications within stages"
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as CardSort)}
            className="bg-slate-900 border border-slate-700 text-slate-200 text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-amber-500"
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
      <div className="flex-1 overflow-x-auto p-6 bg-slate-950">
        {isLoading ? (
          <div className="flex items-center justify-center h-64 text-slate-400">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500"></div>
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
                    className="w-12 flex-shrink-0 bg-slate-900/60 hover:bg-slate-900 border border-slate-800/80 hover:border-slate-700 rounded-2xl flex flex-col items-center py-4 cursor-pointer transition-all max-h-[calc(100vh-170px)] select-none group shadow-sm"
                    title={`Click to expand ${col.label} (${cards.length} cards)`}
                  >
                    <button
                      type="button"
                      className="p-1 rounded-lg text-slate-400 group-hover:text-amber-400 group-hover:bg-slate-800 transition mb-3"
                      aria-label={`Expand ${col.label}`}
                    >
                      <ChevronRight className="h-4 w-4" />
                    </button>

                    <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold mb-4 ${col.badgeColor}`}>
                      {cards.length}
                    </span>

                    <div className="flex-1 flex items-center justify-center">
                      <span className="text-xs font-semibold text-slate-400 group-hover:text-slate-200 tracking-wider [writing-mode:vertical-lr] rotate-180 transition whitespace-nowrap">
                        {col.label}
                      </span>
                    </div>
                  </div>
                );
              }

              return (
                <div
                  key={col.key}
                  className={`w-72 flex-shrink-0 bg-slate-900/70 border ${col.borderColor} rounded-2xl flex flex-col max-h-[calc(100vh-170px)]`}
                >
                  {/* Column Header */}
                  <div className="p-3.5 border-b border-slate-800/80 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-slate-200">{col.label}</span>
                      <span className={`text-xs px-2 py-0.5 rounded-full font-bold ${col.badgeColor}`}>
                        {cards.length}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => toggleStageCollapsed(col.key)}
                      className="p-1 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition"
                      title={`Collapse ${col.label} column`}
                      aria-label={`Collapse ${col.label}`}
                    >
                      <ChevronLeft className="h-4 w-4" />
                    </button>
                  </div>

                  {/* Card List */}
                  <div className="p-3 overflow-y-auto space-y-3 flex-1">
                    {cards.length === 0 ? (
                      <div className="py-8 text-center text-xs text-slate-600 border border-dashed border-slate-800 rounded-xl">
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
                            className={`group relative bg-slate-950/80 border rounded-xl p-3.5 hover:shadow-lg hover:border-slate-600 transition flex flex-col justify-between ${
                              isOutcomeRejected
                                ? 'border-red-950/80 opacity-75'
                                : isOutcomeOffer
                                ? 'border-emerald-700/80'
                                : 'border-slate-800'
                            }`}
                          >
                            {/* Card Top: Company & Days */}
                            <div>
                              <div className="flex items-start justify-between gap-2 mb-1.5">
                                <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300 truncate">
                                  <Building2 className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
                                  <span className="truncate">{card.company}</span>
                                </div>

                                {card.current_stage === 'closed' ? (
                                  card.outcome === 'rejected' ? (
                                    <button
                                      type="button"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        onMoveStage(card.application_id, 'closed', 'clear');
                                      }}
                                      className="text-[10px] uppercase tracking-wider font-bold px-2 py-0.5 rounded-full bg-red-950 text-red-300 border border-red-800 hover:bg-red-900 transition flex items-center gap-1 shadow-sm"
                                      title="Rejected application. Click to clear outcome."
                                    >
                                      <span className="text-red-400">✕</span>
                                      <span>Rejected</span>
                                    </button>
                                  ) : (
                                    <button
                                      type="button"
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        onMoveStage(card.application_id, 'closed', 'rejected');
                                      }}
                                      className="text-[10px] text-slate-500 hover:text-red-400 hover:border-red-900 border border-dashed border-slate-800 rounded px-1.5 py-0.5 transition"
                                      title="Click to add Rejected label"
                                    >
                                      + Rejected
                                    </button>
                                  )
                                ) : (card.current_stage === 'closed' || card.current_stage === 'offer') && card.outcome ? (
                                  <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${
                                    isOutcomeRejected
                                      ? 'bg-red-950 text-red-400 border border-red-800'
                                      : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                                  }`}>
                                    {card.outcome}
                                  </span>
                                ) : null}
                              </div>

                              {/* Title */}
                              <h4
                                onClick={() => onSelectJob(card.job_id)}
                                className="text-xs font-bold text-white group-hover:text-amber-400 transition cursor-pointer line-clamp-2"
                              >
                                {card.title}
                              </h4>

                              {/* Tags */}
                              <div className="flex flex-wrap items-center gap-2 mt-2 text-[11px] text-slate-400">
                                {card.location && (
                                  <span className="flex items-center gap-1 text-slate-400 truncate max-w-[150px]">
                                    <MapPin className="h-3 w-3 text-slate-500" />
                                    <span className="truncate">{card.location}</span>
                                  </span>
                                )}
                              </div>

                              {/* Timeline indicator & Touchpoints */}
                              <div className="flex items-center justify-between text-[10px] text-slate-500 mt-3 pt-2 border-t border-slate-800/80">
                                {daysAgo && (
                                  <span className="flex items-center gap-1 text-slate-400">
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
                                      STRONG_KNOCK: { label: 'STRONG', icon: '🎯', style: 'text-emerald-400 bg-emerald-950/80 border-emerald-800/70' },
                                      SELECTIVE_APPLY: { label: 'SELECTIVE', icon: '⚡', style: 'text-amber-400 bg-amber-950/80 border-amber-800/70' },
                                      HIGH_RISK_LOW_ROI: { label: 'HIGH RISK', icon: '⚠️', style: 'text-rose-400 bg-rose-950/80 border-rose-800/70' },
                                      HARD_PASS: { label: 'PASS', icon: '⛔', style: 'text-slate-400 bg-slate-900 border-slate-700' },
                                      DO_NOT_APPLY: { label: 'PASS', icon: '⛔', style: 'text-slate-400 bg-slate-900 border-slate-700' },
                                    }[decision] || { label: decision.replace(/_/g, ' '), icon: '📋', style: 'text-slate-400 bg-slate-800 border-slate-700' };

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
                                      className="text-slate-400 hover:text-white"
                                      title="Open link"
                                    >
                                      <ExternalLink className="h-3 w-3" />
                                    </a>
                                  )}
                                </div>
                              </div>
                            </div>

                            {/* Quick Action: Advance Stage Selector */}
                            <div className="mt-3 pt-2 border-t border-slate-800/60 flex items-center justify-between">
                              <button
                                onClick={() => onSelectJob(card.job_id)}
                                className="text-[11px] text-slate-400 hover:text-amber-300 transition"
                              >
                                Detail
                              </button>

                              <select
                                value={card.current_stage === 'closed' && card.outcome === 'rejected' ? 'closed:rejected' : card.current_stage}
                                onChange={(e) => {
                                  const val = e.target.value;
                                  if (val === 'closed:rejected') {
                                    onMoveStage(card.application_id, 'closed', 'rejected');
                                  } else if (val === 'closed') {
                                    onMoveStage(card.application_id, 'closed', card.outcome === 'rejected' ? 'clear' : undefined);
                                  } else {
                                    onMoveStage(card.application_id, val);
                                  }
                                }}
                                className="bg-slate-900 border border-slate-700 text-[10px] text-slate-300 rounded px-1.5 py-0.5 focus:outline-none focus:border-amber-500"
                              >
                                {STAGES_CONFIG.filter((s) => s.key !== 'closed').map((s) => (
                                  <option key={s.key} value={s.key}>
                                    Move: {s.label}
                                  </option>
                                ))}
                                <option value="closed">Move: Closed</option>
                                <option value="closed:rejected">Move: Closed (Rejected ❌)</option>
                              </select>
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
