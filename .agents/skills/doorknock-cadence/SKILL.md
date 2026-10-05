---
name: doorknock-cadence
description: Review application evidence, schedule next actions and draft follow-ups without inferring outcomes from silence. (Pillar 4: 候應)
version: 2.0.0
author: DoorKnock Team
platforms: [windows, macos, linux]
metadata:
  tags: [doorknock, cadence, followup, pipeline, review, tracking]
  related_skills: [doorknock-flow, doorknock-knock]
---

# DoorKnock Cadence (候應)

Follow AGENTS.md and the user's scope. Review is diagnostic; a draft is not sent.
Read `docs/cadence.md` at the repository root for the shared policy, vocabulary,
API contract and research basis. This skill and the product use the same rules.

## Separate facts from next actions

Application stage, next action and evidence review are distinct. Use Next actions
for the Dashboard, Email review for Gmail confirmation, and Record review for
missing/ambiguous dates. Display internal `knocked` as Contacted. Only actual
sent role-specific outreach establishes Contacted; a draft or connection
invitation does not. Paused stops active follow-ups without changing stage.
Closed is a confirmed terminal stage with a separate outcome; rejection is
`closed` + `rejected`. Never auto-close or infer ghosted from elapsed time.

## Timing defaults

- Website application: check at 10 weekdays after submission. With no suitable
  contact, check the portal instead of manufacturing an email task.
- Recruiter/referral interaction: 5 weekdays after a substantive interaction.
- Cold outreach actually sent: 7 weekdays after sending.
- Additional unanswered status follow-up: 7 weekdays after the last sent one.
- Interview completed: thank-you within 24–48 hours. Status query after the
  employer response date +2 weekdays, or interview +7 weekdays if none given.
- Assessment submitted: employer response date +2 weekdays, otherwise +7.
- Scheduled interview / assigned assessment: prepare or complete the task,
  using the confirmed date; suppress ordinary status follow-ups.
- Maximum two unanswered status follow-ups per conversation cycle, then Paused.
  Thank-yous, requested documents and answers to employer questions do not count.
- For no-contact applications, a portal check can leave a single review at 30
  calendar days; once reviewed at/after that point, pause unless resumed.

Weekdays mean Mon–Fri. Known holidays can be handled with a manual later date.
Employer promises, posting review-start dates and manual dates override defaults.
Acknowledgements, notes, rematching and repeated outreach never reset the cycle.
A substantive reply resets it. Resuming after the two-follow-up limit allows a
portal check, not additional automatic outreach. Never guess an unknown date.

## Review workflow

1. Read the existing application, timeline and original correspondence as needed.
2. GET `/api/pipeline/dashboard` and the relevant
   `/api/pipeline/applications/{application_id}/cadence`. Check the action's
   basis, meaningful date, reason, deadline and whether dates need confirmation.
3. GET `/api/gmail/reviews` separately for Email review. A scan does not confirm
   that a proposed event occurred; inspect the source before resolving it.
4. Prioritize interviews and assessment deadlines, then missing evidence,
   follow-ups and status checks. Do not use `updated_at` as a contact date.
5. Use AI judgment to explain the recommendation and uncertainty. Date arithmetic
   comes from the shared scheduler. No unsupported conversion-rate promises.

## Drafting

A brief status query is acceptable: identify the role/date, reaffirm interest,
ask about the next-step timeline and offer relevant information if useful.
New artifacts are optional and must be real, evidence-backed and relevant.
Prefer the existing thread. Coordinate multiple roles involving one contact.
Use `workspace/master_resume/master_evidence.yaml` for candidate claims.
Present drafts for review; do not send, upload or contact anyone.

## Confirmed events and reminder controls

Only after user confirmation, POST
`/api/pipeline/applications/{application_id}/cadence` with a supported event and
actual timezone-aware `occurred_at`. Use `due_date` for interview/assessment
assignment, `expected_response_date` when the employer gave a timeline,
`action_date` for `reminder_set` / `cadence_resumed`, and `review_after` for a
confirmed posting review-start date. `outreach_sent` takes `contact_scope`.
Use `cadence_paused` to stop reminders without closing the application.

Use the same **Update progress** contract as the app: one confirmed event updates
its stage, timeline and next action atomically. Application submission sets Applied;
actual outreach sets Contacted only for an early-stage record; assessment assignment
or submission sets Assessment; interview scheduling uses an explicit `interview_stage`
(`recruiter_screen`, `team_match`, `technical_interview`, `final_round`) and confirmed
`due_date`. Completion retains the interview round. Older historical events must not
regress current progress. Reminder controls never change stage.
For a confirmed stage correction, offer or close, use `stage_updated` with `to_stage`;
closing requires the confirmed `outcome`, and assessment/interview stages require a
deadline/date. Terminal records only reopen through an explicit stage correction.
Do not require a second stage update after recording the same progress. An interview
invitation is not interview completion. Do not infer any outcome from silence.

For legacy records, preserve history and old three-day reminders. Confirm actual
sent dates and structured deadlines from sources; do not invent missing events.
Report what was inspected, what was confirmed and what remains uncertain.


## Accidental Timeline entries

Only when the user identifies an incorrect entry and requests its removal, use
DELETE `/api/pipeline/applications/{application_id}/timeline/{event_id}`. This is
reversible: POST the same URL plus `/restore` to undo. Inspect the resulting stage
and next action. Deleted entries are excluded from reminders; locally retained
Deleted events permit recovery. New progress events can safely restore the previous
state when no later progress supersedes them. Legacy events lacking a full snapshot
preserve the current stage and require review. Never treat deletion as recalling a
sent message or changing Gmail. Reviewing history alone never authorizes deletion.
