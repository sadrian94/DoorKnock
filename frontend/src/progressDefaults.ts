import type { NextAction } from './types';

const ACTION_EVENTS: Partial<Record<NextAction['kind'], string>> = {
  followup: 'follow_up', status_check: 'status_checked', thank_you: 'thank_you_sent',
  assessment: 'assessment_submitted', interview_review: 'interview_completed',
  interview: 'interview_scheduled',
};
const STAGE_EVENTS: Record<string, string> = {
  saved: 'application_submitted', applied: 'application_submitted', knocked: 'outreach_sent',
  assessment: 'assessment_assigned', recruiter_screen: 'interview_scheduled',
  team_match: 'interview_scheduled', technical_interview: 'interview_scheduled',
  final_round: 'interview_scheduled',
};

/** Suggest a confirmed event; never infer completion, contact or an outcome. */
export function defaultProgressEvent(stage: string, kind: NextAction['kind']): string {
  if (stage === 'saved') return 'application_submitted';
  if (stage === 'closed' || stage === 'offer') return 'stage_updated';
  if (kind === 'paused') return 'cadence_resumed';
  return ACTION_EVENTS[kind] || STAGE_EVENTS[stage] || '';
}
