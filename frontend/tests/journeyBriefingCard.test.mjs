import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';

const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');
const cardStart = appSource.indexOf('function BriefingCard(');
const cardEnd = appSource.indexOf('\nfunction IntelligencePanel(', cardStart);
const cardSource = appSource.slice(cardStart, cardEnd);

test('places the existing source-grounded briefing after the Stage 2 map/events workspace', () => {
  assert.match(cardSource, /EXPERIMENTAL · AI ASSISTED · SOURCE GROUNDED/);
  assert.match(cardSource, /<h3 id="briefing-title">AI Journey Briefing<\/h3>/);
  assert.ok(appSource.indexOf('<BriefingCard briefingState={journeyBriefingState} />') > appSource.indexOf('<div className={`workspace workspace-stage-${stage}`}'));
  assert.match(appSource, /<BriefingCard briefingState=\{journeyBriefingState\} \/>/);
});

test('retains validated briefing content and independent loading, insufficient-evidence, and failure states', () => {
  assert.match(cardSource, /briefingState\.result\.overview/);
  assert.match(cardSource, /briefingState\.result\.highlights\.length === 3/);
  assert.match(cardSource, /briefingState\.result\.limitations\.slice\(0, 2\)/);
  for (const status of ['waiting_for_evidence', 'in_progress', 'insufficient_evidence']) assert.match(cardSource, new RegExp(`briefingState\\.status === '${status}'`));
  assert.match(cardSource, /briefing is unavailable right now/);
  assert.match(cardSource, /Deterministic journey evidence remains available/);
  assert.doesNotMatch(cardSource, /fetch\(|startBriefingRequest|serializeBriefingEvidence/);
});
