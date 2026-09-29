# DoorKnock Master Evidence Refinement Rubric (淬金準則)

Use this rubric to find meaningful evidence gaps in `workspace/master_resume/master_evidence.yaml`. For a target role, prioritize relevant dimensions; for a comprehensive pass, apply the dimensions across the full evidence bank.

---

## 1. Common evidence gaps

| Flaw | Definition | Bad Example | Refinement Remedy |
|---|---|---|---|
| **Unclear contribution** | A duty is listed without the candidate's own action. | *"Responsible for cleaning customer billing records in Excel."* | Ask what the candidate changed, checked, or delivered; do not assume a business loss or result. |
| **Unclear result** | Claiming improvement without a basis or observable change. | *"Optimized the process."* | Ask what changed and how it was checked; a documented qualitative result is also useful. |
| **Unclear evidence class** | Blurring project, personal, and paid work. | *"Deployed a production model"* for a classroom exercise. | Name the setting and preserve its actual scope. |

---

## 2. Evidence dimensions

Look for context, personal contribution, method, validation, result, and limitations. These are prompts for gathering facts, not a sentence template. A project may need more than one line to show both method and result.

Do not convert modeled impact into deployed business impact. Preserve estimates and uncertainty explicitly.

---

## 3. Categories

Existing category tags can help locate evidence. They are not an exhaustive taxonomy. Preserve a relevant fact even if it does not fit one of these labels:

1. **`data_bi`**: SQL pipelines, ETL, Power BI/Tableau, data validation, variance reporting, financial reconciliations.
2. **`systems_brd`**: Business Requirements Documents, functional specifications, As-Is/To-Be process mapping, stakeholder alignment.
3. **`contract_governance`**: Vendor SLAs, tender evaluations, quotation audits, budget compliance, capital project variance.
4. **`systems_automation`**: Python scripting, REST API integrations, database schema design, workflow automation.
5. **`operations_automation`**: Preventive maintenance schedules, asset lifecycle workflows, dispatch/logistics reprioritization.

---

## 4. Socratic Elicitation Dialogue Guidelines

When an agent identifies a vague bullet:
1. **Identify the missing fact** (purpose, contribution, method, validation, outcome, or setting).
2. **Ask a crisp question without suggesting a number**:
   - *"What records or checks did you use to reconcile the transactions?"*
   - *"What was the process before the script, and how did you check the new result?"*
3. **Record only verified user confirmations**. Never guess or extrapolate numbers.
