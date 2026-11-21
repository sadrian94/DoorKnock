import React, { useEffect, useState } from 'react';
import { CalendarClock, RefreshCw } from 'lucide-react';
import type { DashboardSummary } from '../types';
import { useTimeSettings } from '../timeSettings';
import { calendarDay, formatDate } from '../time';
import { partitionActions } from '../dailyQueue';
import { DailyActions } from './DailyActions';
import { GmailUpdates } from './GmailUpdates';
import { ApplicationAnalyticsView } from './ApplicationAnalyticsView';
import { workspaceButton } from './DashboardWorkspace';

interface DashboardViewProps {
  data: DashboardSummary | null;
  isLoading: boolean;
  hasError: boolean;
  onRetry: () => void;
  onSelectJob: (jobId: string) => void;
  onApplicationsChanged: () => Promise<void>;
  onOpenSettings: () => void;
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
  data, isLoading, hasError, onRetry, onSelectJob, onApplicationsChanged, onOpenSettings,
}) => {
  const { settings } = useTimeSettings();
  const [now, setNow] = useState(() => new Date());
  const [selectedWeek, setSelectedWeek] = useState('');
  useEffect(() => { const timer = window.setInterval(() => setNow(new Date()), 60000); return () => window.clearInterval(timer); }, []);
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

  const weeks = data.weekly_applications;
  const weeklyTotal = weeks.reduce((sum, week) => sum + week.count, 0);
  const weeklyMax = Math.max(0, ...weeks.map(week => week.count));
  const completeWeeks = weeks.slice(0, -1);
  const weeklyAverage = completeWeeks.length ? (completeWeeks.reduce((sum, week) => sum + week.count, 0) / completeWeeks.length).toFixed(1) : '—';
  const tickTarget = Math.max(1, weeklyMax / 4);
  const tickUnit = 10 ** Math.floor(Math.log10(tickTarget));
  const tickStep = ([1, 2, 5, 10].find(step => step * tickUnit >= tickTarget) ?? 10) * tickUnit;
  const intervals = Math.max(1, Math.ceil(weeklyMax / tickStep));
  const yMax = intervals * tickStep;
  const stageMax = Math.max(1, ...Object.values(data.stage_counts));
  const visibleStages = Object.entries(STAGE_LABELS).filter(([key]) => (data.stage_counts[key] || 0) > 0);
  const groups = partitionActions(data.scheduled_items ?? data.attention_items, settings.timezone, now);
  const today = calendarDay(now.toISOString(), settings.timezone)!;
  const interview = [...groups.today, ...groups.upcoming]
    .flatMap(item => {
      const date = item.kind === 'interview' && item.due_date ? calendarDay(item.due_date, settings.timezone) : null;
      return date && date >= today ? [{ item, date }] : [];
    }).sort((a, b) => a.date.localeCompare(b.date))[0];
  const currentWeek = weeks.at(-1);
  const viewedWeek = weeks.find(week => week.week_start === selectedWeek) ?? currentWeek;
  const cohort = data.analytics?.cohorts['90d'];
  const cards = [
    { label: 'Applied this week', value: currentWeek?.count ?? '—', note: currentWeek ? `Week of ${displayDate(currentWeek.week_start)}` : 'No weekly data' },
    { label: 'Next interview', value: interview ? displayDate(interview.date) : '—', note: interview?.item.company ?? 'None scheduled' },
    { label: 'Actions due', value: groups.today.length, note: 'Today, overdue and to review' },
    { label: 'Application → interview', value: cohort?.applications ? `${(cohort.with_interview / cohort.applications * 100).toFixed(1)}%` : '—', note: cohort?.applications ? `${cohort.with_interview} of ${cohort.applications} · last 90 days` : 'No dated applications in 90 days' },
  ];

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-7 sm:px-7 sm:py-9">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-widest text-ui-ink-amber-400">Job search workspace</p>
          <h2 className="mt-1 text-3xl font-bold tracking-tight text-ui-heading sm:text-4xl">Dashboard</h2>
          <p className="mt-1 text-sm text-ui-muted">See what needs attention today, then review how your applications are progressing.</p>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-xs text-ui-muted">
          <time dateTime={today}>{formatDate(today, settings.timezone, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</time>
          <button onClick={onRetry} disabled={isLoading} className={`inline-flex items-center gap-2 ${workspaceButton}`}><RefreshCw className="h-3.5 w-3.5" /> Refresh</button>
        </div>
      </div>

      {hasError && <p role="alert" className="text-sm text-ui-ink-red-300">The latest dashboard refresh failed. The last loaded records are shown; refresh before recording more progress.</p>}
      <dl aria-label="Application overview" className="grid grid-cols-2 divide-ui-line-soft overflow-hidden rounded-2xl border border-ui-line-soft bg-ui-panel/70 md:grid-cols-4 md:divide-x">
        {cards.map((card, index) => <div key={card.label} className={`min-w-0 px-3 py-3 sm:px-4 ${index % 2 ? 'border-l border-ui-line-soft md:border-l-0' : ''} ${index > 1 ? 'border-t border-ui-line-soft md:border-t-0' : ''}`}>
          <dt className="text-xs text-ui-muted">{card.label}</dt>
          <dd className={`mt-1 text-2xl font-semibold tabular-nums tracking-tight ${index >= 2 ? 'text-ui-ink-amber-400' : 'text-ui-heading'}`}>{card.value}</dd>
          <dd className="mt-1 break-words text-xs text-ui-muted">{card.note}</dd>
        </div>)}
      </dl>
      <div className="grid items-start gap-4 md:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <DailyActions groups={groups} today={today} refreshToken={data} onSelectJob={onSelectJob} onRecorded={onApplicationsChanged} />
        <aside className="grid min-w-0 gap-2 md:pt-12" aria-label="Upcoming and email review">
          <div className="flex min-w-0 items-start gap-3 rounded-2xl border border-ui-line-soft bg-ui-panel/70 p-3 sm:p-4">
            <span className="rounded-lg bg-ui-fill-amber-500/10 p-2 text-ui-ink-amber-400"><CalendarClock className="h-4 w-4" aria-hidden="true" /></span>
            <div className="min-w-0"><h3 className="text-sm font-semibold text-ui-heading">Coming up next</h3>
              <p className="mt-1 break-words text-xs text-ui-body">{interview ? `${interview.item.company} · ${interview.item.title}` : 'No upcoming interview'}</p>
              {interview && <p className="mt-1 text-xs text-ui-muted">{displayDate(interview.date)}{interview.item.current_stage && STAGE_LABELS[interview.item.current_stage] ? ` · ${STAGE_LABELS[interview.item.current_stage]}` : ''}</p>}
            </div>
          </div>
          <GmailUpdates onApplicationsChanged={onApplicationsChanged} onOpenSettings={onOpenSettings} />
        </aside>
      </div>

      <section aria-labelledby="analytics-heading" className="space-y-3">
        <div><h3 id="analytics-heading" className="text-xl font-semibold text-ui-heading">Analytics</h3><p className="mt-1 text-xs text-ui-muted">Review application outcomes and how often you’re applying.</p></div>
        <div className="grid gap-3 lg:grid-cols-2">
        {data.analytics && <ApplicationAnalyticsView data={data.analytics} onSelectJob={onSelectJob} displayDate={(value) => formatDate(value, settings.timezone, { month: 'short', day: 'numeric', year: 'numeric' })} />}
        <section className="min-w-0 rounded-2xl border border-ui-line-soft bg-ui-panel/70 p-5" aria-label="Weekly applications sent">
          <h3 className="font-semibold text-ui-heading">Applications sent by week</h3>
          <p className="mt-1 text-xs text-ui-muted">Last 12 calendar weeks · independent of the conversion filter</p>
          <dl className="mt-3 grid grid-cols-3 gap-2" aria-label="Weekly application metrics">
            {[
              { label: '12-week total', value: weeklyTotal },
              { label: 'Avg. per complete week', value: weeklyAverage },
              { label: 'Peak weekly count', value: weeklyMax },
            ].map(metric => <div className="min-w-0" key={metric.label}>
              <dt className="text-xs text-ui-muted">{metric.label}</dt>
              <dd className="text-xl font-semibold tabular-nums text-ui-heading">{metric.value}</dd>
            </div>)}
          </dl>
          <div className="ml-8 mt-6">
            <div className="relative h-36">
              <div className="pointer-events-none absolute inset-0" aria-hidden="true" data-chart-axis="weekly-applications">
                {Array.from({ length: intervals + 1 }, (_, index) => <div key={index} className="absolute inset-x-0 border-t border-ui-line-soft" style={{ bottom: `${index / intervals * 100}%` }}>
                  <span className="absolute right-full mr-2 -translate-y-1/2 text-right text-[0.625rem] tabular-nums text-ui-muted">{index * tickStep}</span>
                </div>)}
              </div>
              <div className="relative flex h-full items-end gap-1" role="group" aria-label="Weekly application counts">
                {weeks.map((week) => {
                  const height = `${week.count / yMax * 100}%`;
                  return <button key={week.week_start} type="button" onClick={() => setSelectedWeek(week.week_start)} aria-pressed={viewedWeek === week}
                    aria-label={`Week of ${displayDate(week.week_start)}: ${week.count} applications`}
                    className="relative flex h-full min-w-0 flex-1 items-end justify-center rounded-t hover:bg-ui-raised/50 focus-visible:z-10 focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-400">
                    {week.count > 0 && <span aria-hidden="true" className="pointer-events-none absolute left-1/2 mb-0.5 -translate-x-1/2 text-[0.625rem] tabular-nums text-ui-body" style={{ bottom: height }}>{week.count}</span>}
                    <span aria-hidden="true" className={`w-full max-w-7 rounded-t ${viewedWeek === week ? 'bg-ui-fill-amber-500' : 'bg-ui-fill-amber-500/35'}`} style={{ height }} />
                  </button>;
                })}
              </div>
            </div>
            <div className="mt-2 grid grid-cols-3 text-xs text-ui-muted" aria-hidden="true">{[0, 4, 8].map(index => <span key={index}>{weeks[index] ? displayDate(weeks[index].week_start) : ''}</span>)}</div>
          </div>
          {viewedWeek && <p className="mt-3 text-xs text-ui-body" aria-live="polite">Week of {displayDate(viewedWeek.week_start)} · {viewedWeek.count} {viewedWeek.count === 1 ? 'application' : 'applications'}{viewedWeek === currentWeek ? ' · current week (partial)' : ''}</p>}
          <section className="mt-5 border-t border-ui-line-soft pt-4" aria-labelledby="current-pipeline-title">
          <h4 id="current-pipeline-title" className="text-sm font-semibold text-ui-heading">Current pipeline stages</h4>
          <p className="mt-1 text-xs text-ui-muted">Snapshot of current records; stages are not a conversion funnel</p>
          {visibleStages.length === 0 ? (
            <p className="mt-3 text-sm text-ui-subtle">No applications recorded yet.</p>
          ) : (
            <div className="mt-3 space-y-2">
              {visibleStages.map(([key, label]) => {
                const count = data.stage_counts[key] || 0;
                return (
                  <div key={key} className="grid grid-cols-[minmax(6.5rem,9rem)_minmax(0,1fr)_2.75rem] items-center gap-2 text-xs">
                    <span className="break-words text-ui-body">{label}</span>
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
        </section>
        </div>
      </section>
    </div>
  );
};
