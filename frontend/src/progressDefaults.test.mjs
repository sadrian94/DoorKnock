import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
const source = readFileSync(new URL('./progressDefaults.ts', import.meta.url), 'utf8');
const compiled = ts.transpileModule(source, {compilerOptions: {module: ts.ModuleKind.ESNext}}).outputText;
const { defaultProgressEvent } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);

test('saved jobs suggest submission rather than an employer reply', () => {
  assert.equal(defaultProgressEvent('saved', 'closed'), 'application_submitted');
});
test('explicit next actions take precedence over stage fallbacks', () => {
  for (const [stage, kind, expected] of [
    ['applied', 'status_check', 'status_checked'], ['knocked', 'followup', 'follow_up'],
    ['technical_interview', 'thank_you', 'thank_you_sent'],
    ['assessment', 'assessment', 'assessment_submitted'],
    ['recruiter_screen', 'interview_review', 'interview_completed'],
  ]) assert.equal(defaultProgressEvent(stage, kind), expected);
});
test('missing evidence suggests the event needed to repair that evidence', () => {
  for (const [stage, expected] of [
    ['applied', 'application_submitted'], ['knocked', 'outreach_sent'],
    ['assessment', 'assessment_assigned'], ['recruiter_screen', 'interview_scheduled'],
    ['team_match', 'interview_scheduled'], ['technical_interview', 'interview_scheduled'],
    ['final_round', 'interview_scheduled'],
  ]) assert.equal(defaultProgressEvent(stage, 'record_review'), expected);
});
test('paused and terminal records do not suggest new contact or infer an outcome', () => {
  assert.equal(defaultProgressEvent('applied', 'paused'), 'cadence_resumed');
  assert.equal(defaultProgressEvent('closed', 'followup'), 'stage_updated');
  assert.equal(defaultProgressEvent('offer', 'closed'), 'stage_updated');
  assert.equal(defaultProgressEvent('unknown', 'record_review'), '');
});
