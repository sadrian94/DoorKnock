export type GmailReview = {
  message_id: string; received_at: string; event_code: string; proposed_stage: string | null;
  reason_code: string; candidate_application_ids: string[]; status: string;
  resolved_at?: string | null; application_id?: string | null; can_undo?: boolean;
};
export type GmailApplication = { id: string; company: string; title: string; current_stage: string };
export type ReviewChoice = { applicationId: string; stage: string; dueDate: string; outcome: string; editing: boolean };
export type ReviewView = 'pending' | 'processed';
export type ReviewWorkspace = { view: ReviewView; selectedId: string | null; choices: Record<string, ReviewChoice>; loaded?: number };
const key = 'doorknock_gmail_review_workspace';

export function mergeReviews(current: GmailReview[], incoming: GmailReview[], view: ReviewView): GmailReview[] {
  const byId = new Map(current.map(item => [item.message_id, item]));
  incoming.forEach(item => byId.set(item.message_id, item));
  return [...byId.values()].sort((a, b) => {
    const field = view === 'pending' ? 'received_at' : 'resolved_at';
    return (Date.parse(b[field] || b.received_at) - Date.parse(a[field] || a.received_at))
      || (a.message_id < b.message_id ? 1 : a.message_id > b.message_id ? -1 : 0);
  });
}

export function nextReviewId(rows: GmailReview[], id: string): string | null {
  const index = rows.findIndex(item => item.message_id === id);
  return rows[index + 1]?.message_id || rows[index - 1]?.message_id || null;
}

export function applicationChoices(applications: GmailApplication[], candidates: string[], query: string): GmailApplication[] {
  const search = query.trim().toLocaleLowerCase();
  return applications.filter(app => `${app.company} ${app.title}`.toLocaleLowerCase().includes(search))
    .sort((a, b) => Number(candidates.includes(b.id)) - Number(candidates.includes(a.id)) || a.company.localeCompare(b.company) || a.title.localeCompare(b.title));
}

function cleanWorkspace(value: Partial<ReviewWorkspace>): ReviewWorkspace {
  const choices: Record<string, ReviewChoice> = {};
  for (const [id, choice] of Object.entries(value.choices || {}).slice(-500)) {
    if (id.length <= 128 && choice && typeof choice.applicationId === 'string' && typeof choice.stage === 'string'
      && typeof choice.dueDate === 'string' && typeof choice.outcome === 'string' && typeof choice.editing === 'boolean') {
      choices[id] = { applicationId: choice.applicationId.slice(0, 128), stage: choice.stage.slice(0, 40), dueDate: choice.dueDate.slice(0, 10), outcome: choice.outcome.slice(0, 40), editing: choice.editing };
    }
  }
  return { view: value.view === 'processed' ? 'processed' : 'pending', selectedId: typeof value.selectedId === 'string' ? value.selectedId.slice(0, 128) : null, choices,
    ...(Number.isInteger(value.loaded) && value.loaded! > 0 ? { loaded: value.loaded } : {}) };
}

export function readReviewWorkspace(storage: Pick<Storage, 'getItem'>): ReviewWorkspace {
  try { return cleanWorkspace(JSON.parse(storage.getItem(key) || '{}') || {}); }
  catch { return { view: 'pending', selectedId: null, choices: {} }; }
}

export function writeReviewWorkspace(storage: Pick<Storage, 'setItem'>, value: ReviewWorkspace): void {
  try { storage.setItem(key, JSON.stringify(cleanWorkspace(value))); } catch { /* Reviewing must work without browser storage. */ }
}
