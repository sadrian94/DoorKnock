# Follow-up policy v2

Application stage, next action and evidence review are separate. No elapsed-time
rule closes an application or assigns an employer outcome. This policy is shared
by the cadence skill, Dashboard, Kanban and job details.

## Default timing

Count weekdays Monday-Friday, starting after the anchor date. Known holidays
can be handled by setting a later reminder date; there is no automatic holiday
calendar. Calendar dates never shift with time zones.

| Confirmed situation | First action | Still no response |
| --- | --- | --- |
| Website application, no human contact | 10 weekdays after submission; check portal if no suitable contact | 7 weekdays after a sent follow-up; maximum two status follow-ups |
| Recruiter/referral contact | 5 weekdays after a substantive interaction | 7 weekdays after a sent follow-up |
| Initial cold outreach actually sent | 7 weekdays after sending | 7 weekdays after a sent follow-up |
| Interview completed | Thank-you within 24-48 hours, separate from status follow-ups | Employer response date +2 weekdays, otherwise interview +7 weekdays |
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


## Single update entry

Use Update progress once: submission sets Applied; actual outreach sets Contacted
for early stages; assessment received/submitted sets Assessment; interview scheduling
sets the confirmed round. Completion retains its round. Stage, timeline and next
action save atomically. Historical evidence never regresses current stage.
Reminder controls only change reminders. Closing requires a confirmed outcome.

Valid stage IDs: saved, applied, knocked, recruiter_screen, assessment, team_match,
technical_interview, final_round, offer, closed. Contacted displays internal knocked.
