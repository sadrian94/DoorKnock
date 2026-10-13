# Follow-up policy v2

Application stage, next action and evidence review are separate. No elapsed-time
rule closes an application or assigns an employer outcome. This policy is shared
by the cadence skill, Dashboard, Kanban and job details.

## Default timing

Count weekdays Monday–Friday, starting after the anchor date. Known holidays
can be handled by setting a later reminder date; there is no automatic holiday
calendar. Calendar dates never shift with time zones.

| Confirmed situation | First action | Still no response |
| --- | --- | --- |
| Website application, no human contact | 10 weekdays after submission; check portal if no suitable contact | 7 weekdays after a sent follow-up; maximum two status follow-ups |
| Recruiter/referral contact | 5 weekdays after a substantive interaction | 7 weekdays after a sent follow-up |
| Initial cold outreach actually sent | 7 weekdays after sending | 7 weekdays after a sent follow-up |
| Interview completed | Thank-you within 24–48 hours, separate from status follow-ups | Employer response date +2 weekdays, otherwise interview +7 weekdays |
| Assessment submitted | Employer response date +2 weekdays, otherwise submission +7 weekdays | 7 weekdays after a sent follow-up |
| Interview scheduled | Preparation reminder two weekdays before; display confirmed interview date | Suppress ordinary status follow-ups until completion is confirmed |
| Assessment assigned | Reminder two weekdays before; display confirmed deadline | Suppress ordinary status follow-ups until submission is confirmed |

Employer dates and manual reminder dates override defaults. If review begins
after a posting closes, the ten-weekday application window starts after the
later of submission and the confirmed review-start date.

A thank-you, document submission or answer to an employer question is not a
status follow-up. Acknowledgements, note edits, rematching and repeated outreach
do not restart a conversation. A substantive reply starts a new unanswered cycle.
Two unanswered status follow-ups pause further outreach without changing stage
or outcome. Resuming after the limit permits a portal check, not extra automatic
outreach; a substantive reply is needed to restart the follow-up allowance.

For applications with no contact, a completed initial portal check can leave
one review at 30 calendar days after the meaningful anchor. A completed review
at/after that point pauses reminders until explicitly resumed. Uncompleted
actions remain visible until the user records an event or manages reminders;
the system does not send recurring notifications. A record edit is never the
anchor for a status review.

## Vocabulary

| Label | Meaning |
| --- | --- |
| Next actions | Dashboard action list, including interviews and assessments |
| Follow-up due | Suitable contact and an evidence-based follow-up date |
| Status check due | Check a portal or confirm current status; no email required |
| Waiting for response | Action date has not arrived |
| Paused | Active follow-ups paused; stage unchanged |
| Email review | Settings queue for human confirmation of Gmail messages |
| Record review | Missing, ambiguous or unstructured scheduling evidence |
| Contacted | Display label for the existing internal stage `knocked` |
| Closed | Confirmed terminal stage, with a separate outcome |

Overdue describes the user's action date, never an employer outcome. Drafts
and connection invitations are not sent role-specific outreach evidence.

## Confirmation and storage

`GET /api/pipeline/applications/{application_id}/cadence` returns the next action,
its anchor/reason, state and follow-up count. Job details and Kanban return the
same derived action. Dashboard includes due/next-three-day checks and follow-ups,
all scheduled interview/assessment tasks, and incomplete-record reviews.
Next actions sort by action date from earliest to latest, then by action priority
on the same date: interview/assessment, thank-you, record review, follow-up, status
check. Undated records follow dated actions. Company and title break remaining
ties. The action date is used, not the interview date or assessment deadline.

`POST /api/pipeline/applications/{application_id}/cadence` records a confirmed
event and its stage update in one transaction using the existing timeline.
The UI uses one **Update progress** entry: choose what happened, fill the required
round/date and save once. Reminder controls and stage corrections are secondary
options. Application submission sets Applied, actual outreach sets Contacted,
assessment assignment/submission sets Assessment, and interview scheduling sets
the chosen round. Completion retains its round. Later-stage records do not regress
from an outreach update, and historical entries do not overwrite current progress.
Explicit `stage_updated` requires `to_stage`; closing also requires a confirmed
`outcome`. Interview/assessment stage changes require dates. Existing terminal
records require an explicit stage change to reopen. Pausing or changing reminders
only affects reminders. No Gmail mutation or email subject/body/sender intake.

Dashboard action rows offer context-specific confirmation shortcuts and Later.
The same shortcuts appear in job details. Opening a shortcut preselects the event
and shows its actual event time; opening or cancelling never records progress.
Update progress remains available for other events. Saving refreshes the actions.
From this version onward, Later saves tag `reminder_source: later` on the existing
reminder event. Two saved postponements since real progress prompt a tracking
review: Keep waiting preserves the saved date; Pause tracking requires confirming
pause; Close application opens the existing closing form and requires an explicit
outcome. No postponement automatically closes an application. The review is shown
immediately after saving even when the new date is outside Dashboard attention.
A reply, confirmed stage change, interview/assessment progress, sent follow-up or
thank-you, or completed status check resets the count. Acknowledgements and generic
manual reminder edits do not. Deleted events are excluded and restored events are
recounted. Older reminders without a source tag are not guessed to be postponements.
Pausing suppresses scheduled interview/assessment and thank-you reminders as well
as ordinary follow-ups; it does not alter their confirmed stage or deadline.

After at least two confirmed status checks and 30 calendar days without substantive
progress, show the same tracking review. Time is measured from the shared meaningful
event anchor; repeated checks do not restart it. A substantive reply or new scheduled
interview/assessment resets the check cycle. The prompt may mention that the employer
might not respond, but never records ghosting or rejection from silence. Pending
employer timelines and scheduled interview/assessment/thank-you tasks suppress it.
Explicit pause suppresses the review; a later confirmed reminder/resume with a future
date after the latest check defers it. Keep waiting on an automatically paused record
opens Resume reminders with an editable seven-calendar-day date and requires saving.
Why this date shows the status-check count separately from follow-ups and Later uses.
Deleted checks are excluded; restoring them recomputes the review.

Event suggestions use the explicit next action first, then the current stage.
Saved suggests Application submitted; Record review suggests the submission,
outreach or scheduled interview/assessment event needed to confirm its evidence.
Paused suggests Resume reminders; Offer/Closed suggests an explicit stage update
without guessing an outcome. Unrecognized contexts require choosing an event.
Saved jobs without an application record create it only when saving confirmed
progress, using the existing start-application endpoint; opening/cancelling is
read-only. If recording fails after creation, the record stays Saved and retry
reuses it rather than creating another application.

Job details also show Coming next as a tentative preview. Interview completion
and assessment submission must be confirmed before their follow-up dates become
active. After a completed interview, the status follow-up date is previewed while
the thank-you is outstanding. Previews use the same scheduler, create no events,
and are excluded from Dashboard action counts. Replies, pauses and corrections
recompute the preview with the active action.

Supported events: `application_submitted`, `outreach_sent`, `follow_up`,
`message_received` (substantive reply), `acknowledgement`, `interview_scheduled`,
`interview_completed`, `thank_you_sent`, `assessment_assigned`,
`assessment_submitted`, `status_checked`, `cadence_paused`, `cadence_resumed`,
`reminder_set`, `stage_updated`.

`occurred_at` must be an actual past instant with a timezone (defaults to now).
Interview/assessment assignment requires `due_date`; interviews also require
`interview_stage` (`recruiter_screen`, `team_match`, `technical_interview`,
`final_round`). Interview completion can use the current interview round. Resume/set reminder requires
`action_date`. Reply/interview completion/submission may include
`expected_response_date`. Application submission may include `review_after`.
Outreach accepts `contact_scope: cold|warm`. Dates use `YYYY-MM-DD`.

Example, only after the user confirms the event:

```json
{"event_type":"assessment_assigned","occurred_at":"2026-10-01T14:00:00Z","due_date":"2026-10-08"}
```

GET `/followups?days=3` keeps its response envelope but uses the derived schedule.
GET `/stale?days=30` is a compatibility review list based on meaningful events,
not `updated_at`. Neither endpoint writes state.

Legacy three-day reminders and history remain intact. The new scheduler ignores
them as defaults. Unknown-zone instants, invalid historical dates, Contacted
without sent evidence, and deadlines only in free text produce Record review.
Confirm structured dates from the original source before scheduling them.

AI helps interpret evidence and draft context-sensitive messages. It must cite
the anchor, explain the suggestion and separate facts from uncertainty. The
shared deterministic scheduler calculates dates. No AI inference turns silence
into rejection, a draft into a sent message, or an invitation into a completed
interview. A concise status query is acceptable; share new work only when real
and relevant. Prefer the original thread and coordinate roles sharing a contact.

## Research basis

Checked 2026-10-01. These defaults are product choices, not universal hiring SLAs.
Berkeley recommends a thank-you within 24 hours and following up after the
employer's expected timeframe; its campus interview guide gives 1–2 weeks as a
typical reference. Harvard recommends a thank-you within 24–48 hours. Microsoft
encourages asking the recruiter for the next-step timeline.

- https://www.career.berkeley.edu/prepare-for-success/interviewing/
- https://www.career.berkeley.edu/prepare-for-success/interviewing/on-campus-interviewing/
- https://careerservices.fas.harvard.edu/resources/interviewing/
- https://careers.microsoft.com/v2/global/en/hiring-tips/interview-tips.html


## Correct an accidental Timeline entry

Timeline offers Delete with inline confirmation and Undo. Deleted events remain
locally recoverable under Deleted events / Restore and are excluded from scheduling,
follow-up counts and current timeline display. The DELETE endpoint is
`/api/pipeline/applications/{application_id}/timeline/{event_id}`; POST its `/restore`
endpoint to restore. Both operations are scoped to the existing application.

New progress events retain before/after state to safely undo the latest stage update
in the same transaction. Later confirmed progress takes priority. Older legacy stage
events have no complete state snapshot: deleting them preserves the current stage
and prompts a manual review rather than inventing an earlier outcome or date.
Deleting a Timeline entry does not recall a real message or change Gmail.
