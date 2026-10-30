import type { AnalysisState } from './analysisTypes';

export type RoadAheadSummary =
  | { status: 'idle' | 'loading' | 'unavailable'; message: string }
  | { status: 'available' | 'partial'; count: number; message: string };

export function roadAheadSummary(analysis: AnalysisState): RoadAheadSummary {
  if (analysis.status === 'idle') return { status: 'idle', message: 'Road Ahead events have not been checked.' };
  if (analysis.status === 'loading') return { status: 'loading', message: 'Checking route-intersecting Road Ahead events…' };
  if (analysis.status === 'error') return { status: 'unavailable', message: 'Road Ahead event count is unavailable because journey analysis failed.' };

  const sources = analysis.result.source_statuses.filter((source) => source.dataset_id.startsWith('road-ahead-'));
  if (!sources.length || !sources.some((source) => source.available)) {
    return { status: 'unavailable', message: 'Road Ahead event count is unavailable; no Road Ahead source data was available.' };
  }

  const count = analysis.result.findings.filter((finding) => finding.classification === 'direct_overlap').length;
  const partial = sources.some((source) => source.stale || !source.available);
  const message = count === 0
    ? partial
      ? 'No route intersections were identified in the partial or stale Road Ahead data. This does not mean roads are clear.'
      : '0 Road Ahead events intersect the selected route in available data. This does not mean roads are clear.'
    : partial
      ? `${count} Road Ahead ${count === 1 ? 'event intersects' : 'events intersect'} the selected route in partial or stale source data.`
      : `${count} Road Ahead ${count === 1 ? 'event intersects' : 'events intersect'} the selected route in available data.`;
  return { status: partial ? 'partial' : 'available', count, message };
}
