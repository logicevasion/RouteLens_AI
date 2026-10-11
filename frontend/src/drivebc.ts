import type { DriveBCAnalysisFinding } from './analysisTypes';

export function driveBCRelationLabel(basis: DriveBCAnalysisFinding['geometry_basis']): string {
  return basis === 'linestring_intersection' ? 'Intersects route geometry'
    : basis === 'point_proximity' ? 'Incident location near route'
      : 'Nearby road event';
}

export function officialDriveBCUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && url.hostname.toLowerCase() === 'api.open511.gov.bc.ca' &&
      !url.port && !url.username && !url.password && !url.search && !url.hash && /^\/events\/[A-Za-z0-9-]+\/?$/.test(url.pathname)
      ? url.toString() : null;
  } catch { return null; }
}
