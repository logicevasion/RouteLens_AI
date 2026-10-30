import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';

const appSource = await readFile(new URL('../src/App.tsx', import.meta.url), 'utf8');
const panelStart = appSource.indexOf('function IntelligencePanel(');
const panelEnd = appSource.indexOf('\nexport default function App()', panelStart);
const panelSource = appSource.slice(panelStart, panelEnd);
const sectionsStart = appSource.indexOf('const intelligenceSections = [');
const sectionsEnd = appSource.indexOf('] as const;', sectionsStart);
const supportingSectionSource = appSource.slice(sectionsStart, sectionsEnd);

test('omits the idle briefing placeholder and renders one card from the existing validated state', () => {
  assert.match(appSource, /const \[journeyBriefingState, setJourneyBriefingState\] = useState<JourneyBriefingState>\(\{ status: 'idle' \}\)/);
  assert.match(appSource, /briefingState=\{journeyBriefingState\}/);
  assert.match(appSource, /briefingState: JourneyBriefingState/);
  assert.match(panelSource, /<h3 id="briefing-title">AI Journey Briefing<\/h3>/);
  assert.match(panelSource, /briefingState\.status !== 'idle'/);
  assert.doesNotMatch(panelSource, /Analyze a selected journey to prepare a source-grounded briefing/);
  assert.ok(panelSource.indexOf('className={`briefing-card') < panelSource.indexOf('className="journey-overview"'));
  assert.ok(panelSource.indexOf('className={`briefing-card') < panelSource.indexOf('className="intelligence-sections"'));
  assert.equal((panelSource.match(/className={`briefing-card/g) ?? []).length, 1);
  assert.doesNotMatch(supportingSectionSource, /AI journey briefing/i);
  assert.match(panelSource, /intelligenceSections\.map\(\(section\)/);
  assert.match(panelSource, /<h3>\{section\.title\}<\/h3>/);
});

test('shows the overview and three ordered topic slots with bounded limitations', () => {
  assert.match(panelSource, /briefingState\.result\.overview/);
  assert.match(panelSource, /briefingState\.result\.highlights\.length === 3/);
  assert.match(panelSource, /briefingState\.result\.highlights\.map\(\(highlight, index\)/);
  assert.match(panelSource, /'Camera conditions'.*'Destination weather'.*'Construction'/s);
  assert.doesNotMatch(panelSource, /highlights\.slice\(0, 4\)/);
  assert.match(panelSource, /briefingState\.result\.limitations\.slice\(0, 2\)/);
  assert.match(panelSource, /highlight\.category/);
  assert.doesNotMatch(panelSource, /JSON\.stringify|result\.usage|returned_model|requested_model|provider/);
});

test('renders evidence wait, generating, insufficient-evidence, and unavailable states clearly', () => {
  for (const status of ['waiting_for_evidence', 'in_progress', 'insufficient_evidence']) {
    assert.match(panelSource, new RegExp(`briefingState\\.status === '${status}'`));
  }
  assert.match(panelSource, /briefing is unavailable right now/);
  assert.match(panelSource, /Deterministic journey evidence remains available/);
});
