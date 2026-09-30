import React, { useState } from 'react';
import { ArrowUpRight, CalendarClock, RefreshCw } from 'lucide-react';
import type { DashboardSummary } from '../types';
import { useTimeSettings } from '../timeSettings';
import { formatDate, hasUnknownTimeZone } from '../time';

interface DashboardViewProps {
  data: DashboardSummary | null;
  isLoading: boolean;
  hasError: boolean;
  onRetry: () => void;
  onSelectJob: (jobId: string) => void;
}

const STAGE_LABELS: Record<string, string> = {
  saved: 'Saved',
  applied: 'Applied',
  knocked: 'Knocked',
  recruiter_screen: 'Recruiter screen',
  assessment: 'Assessment',
  team_match: 'Team match',
  technical_interview: 'Technical interview',
  final_round: 'Final round',
  offer: 'Offer',
  closed: 'Closed',
};

export const DashboardView: React.FC<DashboardViewProps> = ({
  data, isLoading, hasError, onRetry, onSelectJob,
}) => {
  const { settings } = useTimeSettings();
  const displayDate = (value: string) => formatDate(value, settings.timezone, { month: 'short', day: 'numeric' });
  const [showAllAttention, setShowAllAttention] = useState(false);
  if (isLoading && !data) {
    return <div className="p-12 text-center text-slate-400">Loading dashboard…</div>;
  }
  if (hasError) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-12 text-slate-300">
        <p>Dashboard data could not be loaded.</p>
        <button onClick={onRetry} className="mt-4 rounded-lg bg-amber-600 px-4 py-2 text-sm text-white">Try again</button>
      </div>
    );
  }
  if (!data) return null;

  const weeklyMax = Math.max(1, ...data.weekly_applications.map((week) => week.count));
  const stageMax = Math.max(1, ...Object.values(data.stage_counts));
  const visibleStages = Object.entries(STAGE_LABELS).filter(([key]) => (data.stage_counts[key] || 0) > 0);
  const cards = [
    { label: 'Saved jobs', value: data.saved_jobs, note: 'Jobs marked saved or ready' },
    { label: 'Applications sent', value: data.submitted, note: 'Records with an applied date' },
    { label: 'In progress', value: data.active, note: 'Excludes saved, offer, and closed' },
    { label: 'Follow-ups due', value: data.followups_due, note: 'Overdue or due within 3 days' },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white">Dashboard</h2>
          <p className="mt-1 text-sm text-slate-400">Application activity and items to review.</p>
        </div>
        <button onClick={onRetry} disabled={isLoading}
          className="flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:bg-slate-900 disabled:opacity-50">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      <section aria-label="Application overview" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
            <p className="text-sm text-slate-400">{card.label}</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-white">{card.value}</p>
            <p className="mt-2 text-xs text-slate-500">{card.note}</p>
          </div>
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-5" aria-label="Weekly applications sent">
          <h3 className="font-semibold text-white">Applications sent by week</h3>
          <p className="mt-1 text-xs text-slate-400">Last 12 calendar weeks · based on recorded applied dates</p>
          <div className="mt-6 flex h-52 items-end gap-2 border-b border-slate-700 pb-2" role="img"
            aria-label={data.weekly_applications.map((week) => `Week of ${week.week_start}: ${week.count}`).join('; ')}>
            {data.weekly_applications.map((week) => (
              <div key={week.week_start} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1"
                title={`Week of ${week.week_start}: ${week.count} applications`}>
                <span className="text-[10px] tabular-nums text-slate-300">{week.count || ''}</span>
                <div className="w-full max-w-9 rounded-t bg-amber-500/85"
                  style={{ height: `${week.count ? Math.max(8, (week.count / weeklyMax) * 160) : 2}px` }} />
              </div>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            {data.weekly_applications.map((week, index) => (
              <span key={week.week_start} className="min-w-0 flex-1 text-center text-[10px] text-slate-500">
                {index % 2 === 0 ? displayDate(week.week_start) : ''}
              </span>
            ))}
          </div>
        </section>

        <section className="min-w-0 rounded-2xl border border-slate-800 bg-slate-900/70 p-5" aria-label="Current pipeline stage distribution">
          <h3 className="font-semibold text-white">Current pipeline stages</h3>
          <p className="mt-1 text-xs text-slate-400">Snapshot of current records; stages are not a conversion funnel</p>
          {visibleStages.length === 0 ? (
            <p className="mt-8 text-sm text-slate-500">No applications recorded yet.</p>
          ) : (
            <div className="mt-6 space-y-3">
              {visibleStages.map(([key, label]) => {
                const count = data.stage_counts[key] || 0;
                return (
                  <div key={key} className="grid grid-cols-[minmax(110px,155px)_1fr_2rem] items-center gap-3 text-xs">
                    <span className="truncate text-slate-300" title={label}>{label}</span>
                    <div className="h-3 rounded-full bg-slate-800">
                      <div className="h-3 rounded-full bg-amber-500/80" style={{ width: `${(count / stageMax) * 100}%` }} />
                    </div>
                    <span className="text-right tabular-nums text-slate-300">{count}</span>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>

      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
        <div className="flex items-center gap-2">
          <CalendarClock className="h-5 w-5 text-amber-400" />
          <h3 className="font-semibold text-white">Needs review</h3>
        </div>
        <p className="mt-1 text-xs text-slate-400">Follow-up dates are reminders; a stale record does not establish an outcome.</p>
        {data.attention_items.length === 0 ? (
          <p className="mt-5 text-sm text-slate-500">No follow-ups due or stale applications.</p>
        ) : (
          <div className="mt-4 divide-y divide-slate-800">
            {(showAllAttention ? data.attention_items : data.attention_items.slice(0, 8)).map((item) => (
              <button key={item.application_id} onClick={() => onSelectJob(item.job_id)}
                className="flex w-full items-center justify-between gap-4 py-3 text-left hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500">
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium text-slate-200">{item.title}</span>
                  <span className="block truncate text-xs text-slate-500">{item.company}</span>
                </span>
                <span className="flex shrink-0 items-center gap-3 text-xs text-slate-400">
                  {item.kind === 'followup' ? `Follow-up ${displayDate(item.date)}` : `Last updated ${displayDate(item.date)}`}
                  {hasUnknownTimeZone(item.date) && ' · time zone not recorded'}
                  <ArrowUpRight className="h-4 w-4" />
                </span>
              </button>
            ))}
          </div>
        )}
        {data.attention_items.length > 8 && (
          <button onClick={() => setShowAllAttention(!showAllAttention)}
            className="mt-4 text-sm font-medium text-amber-400 hover:text-amber-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-500">
            {showAllAttention ? 'Show fewer' : `Show all ${data.attention_items.length} items`}
          </button>
        )}
      </section>
    </div>
  );
};
