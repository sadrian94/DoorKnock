# DoorKnock Cadence Matrix & Follow-Up Protocols (候應節奏矩陣)

This reference outlines the follow-up rhythm, value-add messaging strategies, and stale-job triage rules for DoorKnock applications.

---

## 1. Multi-Touch Cadence Timeline (跟進節奏時間軸)

| Timing | Action Stage | Objective | Message Strategy |
|---|---|---|---|
| **Day 0** | `knocked` or `applied` | Initial Touchpoint | Initial tailored outreach sent (InMail, connection request, or recruiter note). `next_followup_date` set to +4~5 days. |
| **Day 4–5** | Follow-up 1 | Value-Add Nudge | Share a fresh, relevant technical insight or minimal code update. Never send hollow "bumping this" messages. |
| **Day 10–12** | Follow-up 2 | Polite Closing Loop | Professional, low-friction close-the-loop. Acknowledge busy priorities and leave the door open for future contact. |
| **Day 14+** | Stale Triage | Pipeline Hygiene | If no response after 14 days and 2 follow-ups, transition to `closed` (outcome: `ghosted`). Free cognitive bandwidth. |

---

## 2. Value-Add Follow-Up Principles (價值增補型跟進原則)

### Anti-Patterns (Strictly Banned):
- *"Just checking in to see if you received my previous message."*
- *"Bumping this to the top of your inbox."*
- *"I wanted to follow up on my job application."*

### Positive Value-Add Angles:
1. **The Technical Artifact Update**:
   - Reference a specific project commit or minimal reproducer related to their technology stack.
   - *Example*: *"I was thinking further about the data reconciliation challenges at [Company] and pushed a small open-source pipeline using dbt that audits schema drift..."*
2. **The Public Milestone Connection**:
   - Reference a recent tech post, earnings release, or product feature launched by their engineering group.
3. **The Clean Graceful Exit**:
   - *"Assuming the team is focused on high-priority sprints right now. I will let you get back to building and circle back in the future if your engineering needs evolve."*

---

## 3. Pipeline Stages & Valid Outcomes

All pipeline transitions must follow the DoorKnock state contract:

```text
saved ─► applied ─► knocked ─► recruiter_screen ─► assessment
                                                       │
closed ◄─────── offer ◄─────── final_round ◄─── technical_interview
```

- **Valid Stages**: `saved`, `applied`, `knocked`, `recruiter_screen`, `assessment`, `team_match`, `technical_interview`, `final_round`, `offer`, `closed`.
- **Note on "rejected"**: Never use "rejected" as a stage. Transition to stage `closed` with outcome `rejected`.
- **Valid Outcomes**: `offer_accepted`, `offer_declined`, `rejected`, `withdrawn`, `ghosted`.
