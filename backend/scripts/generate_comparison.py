import json
import sqlite3
import sys
from html import escape as escape_html
from pathlib import Path
from app.config import DOORKNOCK_DB_PATH


def _escape_text(value):
    return escape_html("" if value is None else str(value), quote=True)


def generate_compact_english_html(title, company, v1, v2, output_path=None):
    if output_path is None:
        workspace_dir = Path(__file__).resolve().parent.parent.parent / "workspace"
        html_path = workspace_dir / "match_analysis_comparison.html"
    else:
        html_path = Path(output_path)

    # V1 legacy data
    v1_score = _escape_text(v1.get("suitability_score", 92))
    v1_tech = _escape_text(v1.get("technical_fit_score", 95))
    v1_domain = _escape_text(v1.get("domain_fit_score", 90))
    v1_eligibility = _escape_text(v1.get("eligibility_fit_score", 100))
    v1_reason = _escape_text(v1.get("suitability_reason", ""))
    v1_strengths = v1.get("key_strengths", [])
    v1_gaps = v1.get("gaps_or_risks", [])
    v1_strengths_html = "".join(
        f'<li class="bg-slate-950 p-2 rounded border border-slate-800 flex items-start gap-2"><span class="text-slate-500">•</span><span>{_escape_text(value)}</span></li>'
        for value in v1_strengths
    )
    v1_gaps_html = "".join(
        f'<li class="bg-slate-950 p-2 rounded border border-slate-800 flex items-start gap-2"><span class="text-amber-500">▲</span><span>{_escape_text(value)}</span></li>'
        for value in v1_gaps
    )

    # V2 compact streamlined data
    triage = v2.get("triage", {})
    decision_raw = triage.get("decision", "STRONG_KNOCK")
    decision = _escape_text(decision_raw)
    dealbreakers = triage.get("dealbreakers_detected", ["None"])
    dealbreaker_str = ", ".join(_escape_text(value) for value in dealbreakers) if dealbreakers else "None"
    thesis = _escape_text(triage.get("strategic_thesis", ""))

    mandate = v2.get("employer_mandate", {})
    frictions = mandate.get("acute_operational_frictions", [])
    frictions_html = "".join(
        f'<li class="text-xs text-slate-300 bg-slate-900 p-2 rounded border border-slate-800 flex items-start gap-2"><span class="text-amber-500">🔥</span><span>{_escape_text(value)}</span></li>'
        for value in frictions
    )
    val_hook = _escape_text(mandate.get("immediate_value_hook", ""))

    gaps_mitigation = v2.get("gaps_and_mitigation", [])
    gaps_mitigation_html = "".join(
        f"""<div class="bg-slate-900 p-3 rounded-lg border border-slate-800">
                <div class="flex items-start justify-between gap-3 mb-1">
                  <span>▲ Gap:</span> <span>{_escape_text(g.get('gap'))}</span>
                  <span class="text-[10px] px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">{_escape_text(g.get('severity', 'MODERATE'))}</span>
                </div>
                <p class="text-xs text-slate-300 leading-relaxed mt-2">
                  <span class="text-emerald-400 font-semibold">🛡️ Defense / Mitigation:</span> {_escape_text(g.get('compensating_evidence'))}
                </p>
              </div>"""
        for g in gaps_mitigation
    )

    tailor_dir = v2.get("tactical_directives", {}).get("tailor", {})
    hero_role = _escape_text(tailor_dir.get("hero_role_anchor", "Operations & Financial Data Analyst"))
    supporting = tailor_dir.get("supporting_roles", [])
    supporting_html = ", ".join(_escape_text(value) for value in supporting)
    skill_tax = tailor_dir.get("recommended_skill_taxonomy", [])
    skill_tax_html = "".join(
        f'<div class="p-1.5 rounded bg-slate-950 border border-slate-800 text-[10px] text-amber-300 font-medium text-center">{_escape_text(category.get("category_name"))}</div>'
        for category in skill_tax
    )
    featured_proj = tailor_dir.get("featured_projects", [{}])[0]
    featured_project_name = _escape_text(featured_proj.get("project_name", "Customer Churn & Retention"))
    featured_bullet_label = _escape_text(featured_proj.get("focal_bullet_label", "Pipeline & Architecture"))

    badge_class = "bg-emerald-500/20 text-emerald-300 border-emerald-500/40" if decision_raw == "STRONG_KNOCK" else "bg-blue-500/20 text-blue-300 border-blue-500/40"
    safe_title = _escape_text(title)
    safe_company = _escape_text(company)

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>DoorKnock Match Analysis Redesign: V1 vs V2</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <style>
    body {{ font-family: 'Plus Jakarta Sans', sans-serif; }}
    code, pre, .font-mono {{ font-family: 'JetBrains Mono', monospace; }}
  </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen antialiased selection:bg-amber-500 selection:text-slate-950 p-6 md:p-10">

  <!-- Header -->
  <header class="max-w-6xl mx-auto mb-8 pb-5 border-b border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
    <div>
      <div class="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-amber-500/10 border border-amber-500/30 text-amber-400 text-xs font-semibold uppercase tracking-wider mb-2">
        DoorKnock Architectural Evolution
      </div>
      <h1 class="text-2xl md:text-3xl font-bold text-white tracking-tight">
        Match Analysis Redesign: Compact & Actionable
      </h1>
      <p class="text-slate-400 text-sm mt-1">
        High-signal 4-card Tactical Brief: Decision, Friction, Gaps & Defense, and Resume Blueprint.
      </p>
    </div>
    <div class="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-xs">
      <div class="text-slate-400 uppercase tracking-wider text-[10px] font-bold">Target Job</div>
      <div class="font-bold text-white text-sm">{safe_title}</div>
      <div class="text-amber-400 font-medium">@ {safe_company}</div>
    </div>
  </header>

  <!-- Architectural Shift Callout -->
  <div class="max-w-6xl mx-auto mb-8 bg-slate-900/60 border border-slate-800 rounded-xl p-4 text-xs grid grid-cols-1 md:grid-cols-2 gap-4">
    <div class="flex items-start gap-2.5">
      <div class="p-1.5 rounded-lg bg-red-500/10 text-red-400 border border-red-500/20 font-bold">V1 Flaw</div>
      <div class="text-slate-300">
        <b>Arbitrary Vanity Gauges & Bare Gaps</b>: Abstract percentages (92%) with verbose prose. Gaps are dumped without mitigation or strategic defense.
      </div>
    </div>
    <div class="flex items-start gap-2.5">
      <div class="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">V2 Design</div>
      <div class="text-slate-300">
        <b>Actionable Tactical Brief</b>: Triage decision, acute employer friction, <b>concrete gap mitigation</b>, and resume blueprint. Outreach deferred to <i>Gatekeeper Recon</i>.
      </div>
    </div>
  </div>

  <!-- Comparison Grid -->
  <main class="max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">

    <!-- LEFT: V1 CURRENT SYSTEM -->
    <section class="bg-slate-900/40 border border-slate-800 rounded-xl p-5 space-y-5">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3">
        <div>
          <span class="text-xs font-bold text-slate-400 uppercase tracking-wider">V1 (Status Quo)</span>
          <h2 class="text-base font-bold text-slate-300">Vanity Scores & Verbose Dumps</h2>
        </div>
        <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-slate-800 text-slate-400 border border-slate-700">
          Bloated & Passive
        </span>
      </div>

      <!-- Vanity Gauges -->
      <div class="space-y-2">
        <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400">1. Arbitrary Percentage Gauges</div>
        <div class="grid grid-cols-3 gap-2">
          <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
            <div class="text-[10px] text-slate-500 uppercase">Technical</div>
            <div class="text-lg font-bold text-emerald-400">{v1_tech}%</div>
          </div>
          <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
            <div class="text-[10px] text-slate-500 uppercase">Domain</div>
            <div class="text-lg font-bold text-blue-400">{v1_domain}%</div>
          </div>
          <div class="bg-slate-950 p-2.5 rounded-lg border border-slate-800 text-center">
            <div class="text-[10px] text-slate-500 uppercase">Eligibility</div>
            <div class="text-lg font-bold text-amber-400">{v1_eligibility}%</div>
          </div>
        </div>
        <div class="text-center text-xs text-slate-400 bg-slate-950/60 py-1.5 rounded border border-slate-800">
          Overall Fit: <span class="font-bold text-amber-400">{v1_score}%</span> (Provides no concrete action)
        </div>
      </div>

      <!-- Long verbose text -->
      <div class="space-y-1.5">
        <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400">2. Long Suitability Justification</div>
        <p class="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-lg border border-slate-800">
          {v1_reason}
        </p>
      </div>

      <!-- Verbose strengths -->
      <div class="space-y-1.5">
        <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400">3. Generic Strengths Checklist</div>
        <ul class="space-y-1.5 text-xs text-slate-300">
          {v1_strengths_html}
        </ul>
      </div>

      <!-- Bare gaps without mitigation -->
      <div class="space-y-1.5">
        <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400">4. Bare Gaps (No Strategic Defense)</div>
        <ul class="space-y-1.5 text-xs text-slate-300">
          {v1_gaps_html}
        </ul>
      </div>
    </section>

    <!-- RIGHT: V2 STREAMLINED TACTICAL BRIEF -->
    <section class="bg-gradient-to-b from-amber-950/20 via-slate-900 to-slate-900 border-2 border-amber-500/40 rounded-xl p-5 space-y-5 shadow-2xl">
      <div class="flex items-center justify-between border-b border-amber-900/40 pb-3">
        <div>
          <span class="text-xs font-bold text-amber-400 uppercase tracking-wider">V2 (Redesigned)</span>
          <h2 class="text-base font-bold text-white">Compact Tactical Brief</h2>
        </div>
        <span class="px-2 py-0.5 rounded text-[11px] font-semibold bg-amber-500/20 text-amber-300 border border-amber-500/40">
          High-Signal & Actionable
        </span>
      </div>

      <!-- Card 1: Triage Gate -->
      <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Card 1: Triage & Dealbreakers</span>
          <span class="text-xs font-bold px-2.5 py-0.5 rounded-full border {badge_class}">
            {decision}
          </span>
        </div>
        <p class="text-xs text-slate-200 leading-relaxed">
          <span class="text-amber-400 font-semibold">Strategic Rationale:</span> {thesis}
        </p>
        <div class="text-[11px] text-slate-400 pt-1.5 border-t border-slate-800/80 flex items-center justify-between">
          <span>Dealbreaker Check:</span>
          <span class="text-emerald-400 font-medium">✓ {dealbreaker_str}</span>
        </div>
      </div>

      <!-- Card 2: Acute Friction & Value Hook -->
      <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Card 2: Acute Friction & Hook</span>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
            Role: Builder
          </span>
        </div>
        <div class="space-y-1">
          <div class="text-[11px] font-semibold text-amber-400">Employer's Immediate Bottleneck:</div>
          <ul class="space-y-1">
            {frictions_html}
          </ul>
        </div>
        <div class="text-xs text-slate-300 bg-amber-950/20 p-2.5 rounded border border-amber-900/30">
          <span class="text-amber-300 font-bold">Day-1 Antidote:</span> {val_hook}
        </div>
      </div>

      <!-- Card 3: Identified Gaps & Strategic Defense -->
      <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-2.5">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Card 3: Gaps & Strategic Defense</span>
          <span class="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
            Risk Analysis
          </span>
        </div>
        <div class="space-y-2">
          {gaps_mitigation_html}
        </div>
      </div>

      <!-- Card 4: Resume Tailoring Blueprint -->
      <div class="bg-slate-950 p-4 rounded-xl border border-slate-800 space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-[11px] font-bold uppercase tracking-wider text-slate-400">Card 4: Resume Blueprint</span>
          <span class="text-[10px] text-slate-400 font-mono">For doorknock-tailor</span>
        </div>
        
        <div class="space-y-2 text-xs">
          <!-- Hero Role -->
          <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
            <div class="text-[10px] text-slate-400 uppercase font-semibold">Hero Anchor Role (3-4 bullets):</div>
            <div class="font-bold text-white mt-0.5">{hero_role}</div>
            <div class="text-[11px] text-slate-400 mt-0.5">Supporting: {supporting_html}</div>
          </div>

          <!-- Dynamic Skill Buckets -->
          <div class="bg-slate-900 p-2.5 rounded border border-slate-800">
            <div class="text-[10px] text-slate-400 uppercase font-semibold mb-1">Dynamic Skill Taxonomy (JD-Aligned):</div>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
              {skill_tax_html}
            </div>
          </div>

          <!-- Spotlight Project -->
          <div class="bg-slate-900 p-2.5 rounded border border-slate-800 flex items-center justify-between">
            <div>
              <div class="text-[10px] text-slate-400 uppercase font-semibold">Spotlight Project:</div>
              <div class="text-[11px] text-slate-200 font-medium">{featured_project_name}</div>
            </div>
            <span class="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              {featured_bullet_label}
            </span>
          </div>
        </div>
      </div>

      <!-- Pipeline Handoff Note -->
      <div class="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800 text-[11px] text-slate-400 flex items-center justify-between">
        <span>🚪 <b>Outreach Phase</b>:</span>
        <span class="text-slate-300">Deferred to <i>Gatekeeper Recon (Pillar 1)</i> once gatekeeper contact is confirmed.</span>
      </div>

    </section>

  </main>

  <footer class="max-w-6xl mx-auto mt-10 text-center text-xs text-slate-500 pb-6 border-t border-slate-800 pt-4">
    DoorKnock Architecture Laboratory • Candidate Fact Grounding Isolated in <code class="text-slate-400">workspace/</code>
  </footer>

</body>
</html>
"""
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(html, encoding="utf-8")
    print(f"Updated compact English HTML with Gaps & Defense at: {html_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: generate_comparison.py <job-id>")

    workspace_dir = Path(__file__).resolve().parent.parent.parent / "workspace"
    sample_json_path = workspace_dir / "v2_analysis_sample.json"
    if not sample_json_path.exists():
        raise SystemExit(f"Comparison input not found: {sample_json_path}")

    v2_analysis = json.loads(sample_json_path.read_text(encoding="utf-8"))
    with sqlite3.connect(DOORKNOCK_DB_PATH) as conn:
        row = conn.execute(
            "SELECT title, company, analysis_json FROM jobs WHERE id = ?",
            (sys.argv[1],),
        ).fetchone()
    if not row:
        raise SystemExit("No local job matches that ID")
    v1_analysis = json.loads(row[2]) if row[2] else {}
    generate_compact_english_html(row[0], row[1], v1_analysis, v2_analysis)
