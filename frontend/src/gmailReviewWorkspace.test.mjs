import test from 'node:test';
import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import ts from 'typescript';
const path=new URL('./gmailReviewWorkspace.ts',import.meta.url);
const compiled=ts.transpileModule(existsSync(path)?readFileSync(path,'utf8'):'',{compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const { mergeReviews, nextReviewId, readReviewWorkspace, writeReviewWorkspace, applicationChoices }=await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`);
const rows=[{message_id:'new',received_at:'2026-10-16T12:00:00Z'},{message_id:'middle',received_at:'2026-10-16T11:00:00Z'},{message_id:'old',received_at:'2026-10-15T12:00:00Z'}];

test('new mail stays first and loading pages never duplicates a message',()=>{
  const merged=mergeReviews([rows[1],rows[2]],[rows[0],rows[1]],'pending');
  assert.deepEqual(merged.map(r=>r.message_id),['new','middle','old']);
});
test('processing advances from current position and handles the last message',()=>{
  assert.equal(nextReviewId(rows,'middle'),'old');
  assert.equal(nextReviewId(rows,'old'),'middle');
  assert.equal(nextReviewId([rows[0]],'new'),null);
});
test('candidate applications come first while search can find another record',()=>{
  const apps=[{id:'other',company:'Cedar Works',title:'Analyst',current_stage:'applied'},{id:'candidate',company:'Example Analytics',title:'Operations',current_stage:'knocked'}];
  assert.deepEqual(applicationChoices(apps,['candidate'],'').map(a=>a.id),['candidate','other']);
  assert.deepEqual(applicationChoices(apps,['candidate'],'CEDAR').map(a=>a.id),['other']);
});
test('refresh keeps the selected mail and per-message choices without storing email text',()=>{
  const values=new Map();const storage={getItem:k=>values.get(k)??null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)};
  const state={view:'pending',selectedId:'middle',loaded:100,choices:{middle:{applicationId:'app-1',stage:'recruiter_screen',dueDate:'2026-10-22',outcome:'',editing:true}},subject:'private text'};
  writeReviewWorkspace(storage,state);
  const restored=readReviewWorkspace(storage);
  assert.equal(restored.selectedId,'middle');
  assert.equal(restored.loaded,100);
  assert.deepEqual(restored.choices.middle,state.choices.middle);
  assert.equal(JSON.stringify(restored).includes('private text'),false);
});
test('damaged and blocked storage do not prevent reviewing',()=>{
  assert.deepEqual(readReviewWorkspace({getItem:()=>'{broken'}),{view:'pending',selectedId:null,choices:{}});
  assert.doesNotThrow(()=>writeReviewWorkspace({setItem(){throw new Error('blocked');}},{view:'pending',selectedId:null,choices:{}}));
});
