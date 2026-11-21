import { useState } from 'react';
import type { ApplicationAnalytics, ApplicationCohortRange, ApplicationMilestone } from '../types';
import { DashboardWorkspace, workspaceButton } from './DashboardWorkspace';

const ranges: { id: ApplicationCohortRange; label: string }[] = [
  { id: '30d', label: 'Last 30 days' },
  { id: '90d', label: 'Last 90 days' },
  { id: 'all', label: 'All time' },
];

type MilestoneKey = ApplicationMilestone | 'applied';

export function ApplicationAnalyticsView({ data, displayDate, onSelectJob }: {
  data: ApplicationAnalytics;
  displayDate: (value: string) => string;
  onSelectJob: (id: string) => void;
}) {
  const [range, setRange] = useState<ApplicationCohortRange>('90d');
  const [selection, setSelection] = useState<{ key: MilestoneKey; label: string; trigger: HTMLButtonElement } | null>(null);
  const cohort = data.cohorts[range];
  const percent = (count: number, total: number) => total ? (count / total) * 100 : null;
  const formatPercent = (value: number | null) => value === null ? '—' : `${value.toFixed(1)}%`;
  const milestones: { key: MilestoneKey; label: string; count: number }[] = [
    { key: 'applied', label: 'Applied', count: cohort.applications },
    { key: 'interview', label: 'Reached interview', count: cohort.with_interview },
    { key: 'completed', label: 'Completed interview', count: cohort.with_completed_interview },
    { key: 'offer', label: 'Received offer', count: cohort.with_offer },
  ];
  const selectedKey = selection?.key;
  const records = selectedKey ? (data.records ?? []).filter(row => (!cohort.start_date || row.applied_date >= cohort.start_date)
    && (selectedKey === 'applied' || !!row.milestones[selectedKey])) : [];

  return (
    <section className="rounded-2xl border border-ui-line-soft bg-ui-panel/30 p-5" aria-labelledby="conversion-title">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h3 id="conversion-title" className="font-semibold text-ui-heading">Application conversions</h3>
          <p className="mt-1 text-sm text-ui-muted">Grouped by application date, with outcomes recorded through {displayDate(data.through_date)}.</p>
        </div>
        <fieldset className="flex flex-wrap gap-1 rounded-lg border border-ui-line p-1">
          <legend className="sr-only">Application date range</legend>
          {ranges.map(({ id, label }) => (
            <label key={id} className="relative cursor-pointer">
              <input type="radio" name="application-cohort-range" className="peer sr-only"
                checked={range === id} onChange={() => setRange(id)} />
              <span className="block rounded-md px-3 py-1.5 text-xs font-medium text-ui-body hover:bg-ui-raised peer-checked:bg-ui-raised peer-checked:text-ui-heading peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-ui-ink-amber-400">{label}</span>
            </label>
          ))}
        </fieldset>
      </div>

      <p className="mt-4 text-xs text-ui-muted">
        {cohort.start_date ? `Applications sent ${displayDate(cohort.start_date)} – ${displayDate(data.through_date)}` : 'All applications with a valid recorded date'}
        {' · '}Each role counts once per milestone; stages may be skipped or unrecorded.
      </p>
      {cohort.applications === 0 ? (
        <p className="mt-5 rounded-lg border border-ui-line-soft px-4 py-3 text-sm text-ui-body" role="status">No dated applications in this range. Conversion rates aren’t available.</p>
      ) : (
        <div className="mt-5 space-y-4">
          <dl className="grid gap-4 rounded-xl border border-ui-line-soft bg-ui-panel/70 p-3 sm:grid-cols-2" aria-label="Conversion summary">
            <div>
              <dt className="text-xs text-ui-muted">Application → interview</dt>
              <dd className="mt-0.5 text-2xl font-semibold tabular-nums text-ui-heading">{formatPercent(percent(cohort.with_interview, cohort.applications))}</dd>
              <dd className="text-xs text-ui-muted">{cohort.with_interview} of {cohort.applications} applications</dd>
            </div>
            <div>
              <dt className="text-xs text-ui-muted">Median time to first interview signal</dt>
              <dd className="mt-0.5 text-lg font-semibold tabular-nums text-ui-heading">
                {cohort.median_days_to_interview === null ? '—' : `${cohort.median_days_to_interview} days`}
              </dd>
              <dd className="text-xs text-ui-muted">Among {cohort.with_interview} with a recorded interview milestone</dd>
            </div>
          </dl>
          <ul className="space-y-3" aria-label="Percent of applications that reached each milestone">
            {milestones.map(({ key, label, count }) => {
              const rate = percent(count, cohort.applications);
              return (
                <li key={label}>
                  <button type="button" aria-haspopup="dialog" aria-controls="conversion-workspace" className="flex w-full items-baseline justify-between gap-2 rounded text-left text-sm hover:bg-ui-raised focus-visible:outline focus-visible:outline-2 focus-visible:outline-ui-ink-amber-400" onClick={event => setSelection({ key, label, trigger: event.currentTarget })}>
                    <span className="text-ui-body">{label}</span>
                    <span className="shrink-0 text-right tabular-nums text-ui-heading">
                      <span className="font-semibold">{count}</span><span className="ml-2 text-xs text-ui-muted">{formatPercent(rate)} <span aria-hidden="true">›</span></span>
                    </span>
                  </button>
                  <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-ui-raised" aria-hidden="true">
                    <div className="h-full rounded-full bg-ui-fill-amber-500/85" style={{ width: `${rate ?? 0}%` }} />
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
      <details className="mt-4 text-xs leading-relaxed text-ui-muted">
        <summary className="cursor-pointer text-ui-body">How these numbers are counted</summary>
        <p className="mt-2">Interview means a recorded screen or interview-stage transition, scheduling, or completion. A scheduled interview is not counted as completed. Offer requires a recorded offer or confirmation that an offer was accepted or declined. All milestone rates use applications as the denominator. Recent applications may still advance.</p>
      </details>
      {(data.records_without_valid_applied_date > 0 || data.dated_records_with_unverified_milestones > 0) && (
        <p className="mt-3 text-xs leading-relaxed text-ui-muted">
          All-time data coverage: {data.records_without_valid_applied_date > 0 && `${data.records_without_valid_applied_date} records without a usable application date are excluded. `}
          {data.dated_records_with_unverified_milestones > 0 && `${data.dated_records_with_unverified_milestones} dated applications lack timeline evidence for their recorded interview or offer status.`}
        </p>
      )}
      <DashboardWorkspace id="conversion-workspace" size="compact" title={selection?.label ?? 'Application records'}
        description={`${records.length} ${records.length === 1 ? 'application' : 'applications'} · ${ranges.find(item => item.id === range)?.label}`}
        open={!!selection} trigger={selection?.trigger ?? null} onClose={() => setSelection(null)}>
        {selection && <ul className="divide-y divide-ui-line-soft px-4 py-2 sm:px-6">
          {!records.length && <li className="py-4 text-sm text-ui-muted">No application records for this milestone in the selected range.</li>}
          {records.map(row => <li key={row.job_id} className="py-3"><details>
            <summary className="cursor-pointer break-words text-sm font-semibold text-ui-heading">{row.title} · {row.company} <span className="font-normal text-ui-muted">· Applied {displayDate(row.applied_date)}</span></summary>
            <ol className="my-2 space-y-1 pl-4 text-xs text-ui-muted">
              <li>{displayDate(row.applied_date)} · Applied</li>
              {milestones.flatMap(({ key, label }) => key !== 'applied' && row.milestones[key] ? [{ date: row.milestones[key]!, label }] : [])
                .sort((a, b) => a.date.localeCompare(b.date)).map(step => <li key={step.label}>{displayDate(step.date)} · {step.label}</li>)}
            </ol>
            <button type="button" className={workspaceButton} onClick={() => { setSelection(null); onSelectJob(row.job_id); }}>Open application details</button>
          </details></li>)}
        </ul>}
      </DashboardWorkspace>
    </section>
  );
}
