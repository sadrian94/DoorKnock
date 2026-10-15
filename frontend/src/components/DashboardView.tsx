import React from 'react';
import { RefreshCw } from 'lucide-react';
import type { DashboardSummary } from '../types';
import { useTimeSettings } from '../timeSettings';
import { formatDate } from '../time';
import { DailyActions } from './DailyActions';

interface DashboardViewProps {
  data: DashboardSummary | null;
  isLoading: boolean;
  hasError: boolean;
  onRetry: () => void;
  onSelectJob: (jobId: string) => void;
  onApplicationsChanged: () => Promise<void>;
}

const STAGE_LABELS: Record<string, string> = {
  saved: 'Saved',
  applied: 'Applied',
  knocked: 'Contacted',
  recruiter_screen: 'Recruiter screen',
  assessment: 'Assessment',
  team_match: 'Team match',
  technical_interview: 'Technical interview',
  final_round: 'Final round',
  offer: 'Offer',
  closed: 'Closed',
};

export const DashboardView: React.FC<DashboardViewProps> = ({
  data, isLoading, hasError, onRetry, onSelectJob, onApplicationsChanged,
}) => {
  const { settings } = useTimeSettings();
  const displayDate = (value: string) => formatDate(value, settings.timezone, { month: 'short', day: 'numeric' });
  if (isLoading && !data) {
    return <div className="p-12 text-center text-ui-muted">Loading dashboard…</div>;
  }
  if (hasError && !data) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-12 text-ui-body">
        <p>Dashboard data could not be loaded.</p>
        <button onClick={onRetry} className="mt-4 rounded-lg bg-ui-fill-amber-600 px-4 py-2 text-sm text-ui-on-action">Try again</button>
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
    { label: 'Follow-up due', value: data.followups_due, note: `${data.status_checks_due} status checks · due or within 3 days` },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-7">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-ui-heading">Dashboard</h2>
          <p className="mt-1 text-sm text-ui-muted">Work through today’s actions, then review your application activity.</p>
        </div>
        <button onClick={onRetry} disabled={isLoading}
          className="flex items-center gap-2 rounded-lg border border-ui-line px-3 py-2 text-sm text-ui-body hover:bg-ui-panel disabled:opacity-50">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {hasError && <p role="alert" className="text-sm text-ui-ink-red-300">The latest dashboard refresh failed. The last loaded records are shown; refresh before recording more progress.</p>}
      <DailyActions refreshToken={data} items={data.scheduled_items || data.attention_items} onSelectJob={onSelectJob} onRecorded={onApplicationsChanged} />

      <section aria-label="Application overview" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map((card) => (
          <div key={card.label} className="rounded-2xl border border-ui-line-soft bg-ui-panel/70 p-5">
            <p className="text-sm text-ui-muted">{card.label}</p>
            <p className="mt-2 text-3xl font-semibold tabular-nums text-ui-heading">{card.value}</p>
            <p className="mt-2 text-xs text-ui-subtle">{card.note}</p>
          </div>
        ))}
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <section className="min-w-0 rounded-2xl border border-ui-line-soft bg-ui-panel/70 p-5" aria-label="Weekly applications sent">
          <h3 className="font-semibold text-ui-heading">Applications sent by week</h3>
          <p className="mt-1 text-xs text-ui-muted">Last 12 calendar weeks · based on recorded applied dates</p>
          <div className="mt-6 flex h-52 items-end gap-2 border-b border-ui-line pb-2" role="img"
            aria-label={data.weekly_applications.map((week) => `Week of ${week.week_start}: ${week.count}`).join('; ')}>
            {data.weekly_applications.map((week) => (
              <div key={week.week_start} className="flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1"
                title={`Week of ${week.week_start}: ${week.count} applications`}>
                <span className="text-[0.625rem] tabular-nums text-ui-body">{week.count || ''}</span>
                <div className="w-full max-w-9 rounded-t bg-ui-fill-amber-500/85"
                  style={{ height: `${week.count ? Math.max(8, (week.count / weeklyMax) * 160) : 2}px` }} />
              </div>
            ))}
          </div>
          <div className="mt-2 flex gap-2">
            {data.weekly_applications.map((week, index) => (
              <span key={week.week_start} className="min-w-0 flex-1 text-center text-[0.625rem] text-ui-subtle">
                {index % 2 === 0 ? displayDate(week.week_start) : ''}
              </span>
            ))}
          </div>
        </section>

        <section className="min-w-0 rounded-2xl border border-ui-line-soft bg-ui-panel/70 p-5" aria-label="Current pipeline stage distribution">
          <h3 className="font-semibold text-ui-heading">Current pipeline stages</h3>
          <p className="mt-1 text-xs text-ui-muted">Snapshot of current records; stages are not a conversion funnel</p>
          {visibleStages.length === 0 ? (
            <p className="mt-8 text-sm text-ui-subtle">No applications recorded yet.</p>
          ) : (
            <div className="mt-6 space-y-3">
              {visibleStages.map(([key, label]) => {
                const count = data.stage_counts[key] || 0;
                return (
                  <div key={key} className="grid grid-cols-[minmax(110px,155px)_1fr_2rem] items-center gap-3 text-xs">
                    <span className="truncate text-ui-body" title={label}>{label}</span>
                    <div className="h-3 rounded-full bg-ui-raised">
                      <div className="h-3 rounded-full bg-ui-fill-amber-500/80" style={{ width: `${(count / stageMax) * 100}%` }} />
                    </div>
                    <span className="text-right tabular-nums text-ui-body">{count}</span>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </div>


    </div>
  );
};
