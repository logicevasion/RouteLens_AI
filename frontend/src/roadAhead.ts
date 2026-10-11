import type { FeatureCollection } from 'geojson';
import type { AnalysisFinding, CityEvent, DriveBCAnalysisFinding, DriveBCGeometryBasis, JourneyAnalysis, RegionalEvent, RegionalGeometry, RoadAheadGeometry } from './analysisTypes';
import type { Location } from './locationTypes';
import type { RouteCandidate } from './routeTypes';
import { normalizeDestinationWeather } from './weather';

export type RoadAheadFeatureProperties = {
  eventId: string;
  classification: AnalysisFinding['classification'];
  selected: boolean;
};

export type RoadAheadFeatureCollection = FeatureCollection<
  Exclude<RoadAheadGeometry, { type: 'GeometryCollection' }> | Extract<RoadAheadGeometry, { type: 'GeometryCollection' }>,
  RoadAheadFeatureProperties
>;

function validPosition(value: unknown): value is number[] {
  return Array.isArray(value) && value.length >= 2 &&
    typeof value[0] === 'number' && Number.isFinite(value[0]) && value[0] >= -180 && value[0] <= 180 &&
    typeof value[1] === 'number' && Number.isFinite(value[1]) && value[1] >= -90 && value[1] <= 90 &&
    value.slice(2).every((item) => typeof item === 'number' && Number.isFinite(item));
}

function usableGeometry(value: unknown): RoadAheadGeometry | null {
  if (!value || typeof value !== 'object' || !('type' in value)) return null;
  const candidate = value as { type: unknown; coordinates?: unknown; geometries?: unknown };
  const coordinates = candidate.coordinates;
  if (candidate.type === 'Point') return validPosition(coordinates) ? value as RoadAheadGeometry : null;
  if (candidate.type === 'LineString') {
    if (Array.isArray(coordinates) && coordinates.length >= 2 && coordinates.every(validPosition)) return value as RoadAheadGeometry;
    return null;
  }
  if (candidate.type === 'MultiLineString') {
    if (Array.isArray(coordinates) && coordinates.length > 0 && coordinates.every((line) =>
      Array.isArray(line) && line.length >= 2 && line.every(validPosition),
    )) return value as RoadAheadGeometry;
    return null;
  }
  if (candidate.type === 'Polygon') {
    if (Array.isArray(coordinates) && coordinates.length > 0 && coordinates.every((ring) =>
      Array.isArray(ring) && ring.length >= 4 && ring.every(validPosition) &&
      ring[0][0] === ring[ring.length - 1][0] && ring[0][1] === ring[ring.length - 1][1],
    )) return value as RoadAheadGeometry;
    return null;
  }
  if (candidate.type === 'GeometryCollection' && Array.isArray(candidate.geometries)) {
    const geometries = candidate.geometries.map(usableGeometry).filter((geometry): geometry is RoadAheadGeometry => geometry !== null);
    return geometries.length ? { type: 'GeometryCollection', geometries } : null;
  }
  return null;
}

export function hasUsableGeometry(geometry: RoadAheadGeometry | null): boolean {
  return usableGeometry(geometry) !== null;
}

export function roadAheadGeoJson(findings: AnalysisFinding[], selectedEventId: string | null): RoadAheadFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: findings.flatMap((finding) => {
      const geometry = usableGeometry(finding.event.geometry);
      if (!geometry) return [];
      return [{
        type: 'Feature' as const,
        id: sourceScopedEventId(finding.event),
        properties: {
          eventId: finding.event.id,
          classification: finding.classification,
          selected: sourceScopedEventId(finding.event) === selectedEventId,
        },
        geometry,
      }];
    }),
  };
}

export function eventBounds(geometry: RoadAheadGeometry | null): [[number, number], [number, number]] | null {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  const addPosition = (position: unknown) => {
    if (!validPosition(position)) return;
    west = Math.min(west, position[0]);
    south = Math.min(south, position[1]);
    east = Math.max(east, position[0]);
    north = Math.max(north, position[1]);
  };
  const visit = (item: RoadAheadGeometry) => {
    if (item.type === 'GeometryCollection') item.geometries.forEach(visit);
    else if (item.type === 'Point') addPosition(item.coordinates);
    else if (item.type === 'LineString') item.coordinates.forEach(addPosition);
    else item.coordinates.flat(1).forEach(addPosition);
  };
  const valid = geometry && usableGeometry(geometry);
  if (valid) visit(valid);
  return Number.isFinite(west) ? [[west, south], [east, north]] : null;
}

export function sourceScopedEventId(event: Pick<CityEvent, 'source_dataset_id' | 'source_record_id'>): string {
  return `${event.source_dataset_id}:${event.source_record_id}`;
}

export function regionalGeometry(value: unknown): RegionalGeometry | null {
  if (!isRecord(value)) return null;
  if (value.type === 'Point' && validPosition(value.coordinates)) return value as RegionalGeometry;
  if (value.type === 'LineString' && Array.isArray(value.coordinates) && value.coordinates.length >= 2 && value.coordinates.every(validPosition)) return value as RegionalGeometry;
  return null;
}

export function regionalEventBounds(geometry: RegionalGeometry | null): [[number, number], [number, number]] | null {
  if (!geometry) return null;
  const coordinates = geometry.type === 'Point' ? [geometry.coordinates] : geometry.coordinates;
  const west = Math.min(...coordinates.map((point) => point[0]));
  const east = Math.max(...coordinates.map((point) => point[0]));
  const south = Math.min(...coordinates.map((point) => point[1]));
  const north = Math.max(...coordinates.map((point) => point[1]));
  return [[west, south], [east, north]];
}

export function regionalEventsGeoJson(events: RegionalEvent[], selectedEventId: string | null) {
  return {
    type: 'FeatureCollection' as const,
    features: events.flatMap((event) => {
      const geometry = regionalGeometry(event.geometry);
      if (!geometry) return [];
      const id = sourceScopedEventId(event);
      return [{ type: 'Feature' as const, id, properties: { eventId: id, selected: id === selectedEventId }, geometry }];
    }),
  };
}

export function buildAnalysisRequest(
  origin: JourneyAnalysis['trip']['origin'],
  destination: JourneyAnalysis['trip']['destination'],
  route: { id: string; geometry: JourneyAnalysis['trip']['selected_route']['geometry']; distance_meters: number; duration_seconds: number; label?: string | null },
): JourneyAnalysis['trip'] {
  return {
    origin,
    destination,
    mode: 'drive',
    selected_route: {
      candidate_id: route.id,
      geometry: route.geometry,
      distance_meters: route.distance_meters,
      duration_seconds: route.duration_seconds,
      label: route.label,
    },
  };
}

export function isAnalysisReady(origin: Location | null, destination: Location | null, route: RouteCandidate | null): boolean {
  return Boolean(origin && destination && route && route.geometry.type === 'LineString' &&
    route.geometry.coordinates.length >= 2 && route.geometry.coordinates.every((position) =>
      position.length === 2 && Number.isFinite(position[0]) && Number.isFinite(position[1]) &&
      position[0] >= -180 && position[0] <= 180 && position[1] >= -90 && position[1] <= 90,
    ));
}

export function isCurrentAnalysisRequest(requestId: number, currentId: number, requestKey: string, currentKey: string | null): boolean {
  return requestId === currentId && requestKey === currentKey;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function nullableText(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function normalizeEvent(value: unknown): CityEvent | null {
  if (!isRecord(value) || typeof value.id !== 'string' || typeof value.title !== 'string' ||
      typeof value.event_type !== 'string' || typeof value.source !== 'string' ||
      typeof value.source_dataset_id !== 'string' || typeof value.source_record_id !== 'string') return null;
  return {
    id: value.id,
    source: value.source,
    source_dataset_id: value.source_dataset_id,
    source_record_id: value.source_record_id,
    event_type: value.event_type,
    title: value.title,
    description: nullableText(value.description),
    geometry: usableGeometry(value.geometry),
    latitude: typeof value.latitude === 'number' && Number.isFinite(value.latitude) ? value.latitude : null,
    longitude: typeof value.longitude === 'number' && Number.isFinite(value.longitude) ? value.longitude : null,
    severity: nullableText(value.severity),
    status: nullableText(value.status),
    schedule_text: nullableText(value.schedule_text),
    restriction_text: nullableText(value.restriction_text),
    observed_at: nullableText(value.observed_at),
    updated_at: nullableText(value.updated_at),
    source_url: nullableText(value.source_url),
    relevance_reason: nullableText(value.relevance_reason),
    source_metadata: isRecord(value.source_metadata) ? value.source_metadata : {},
    attribution: typeof value.attribution === 'string' ? value.attribution : 'City of Vancouver Open Data Portal',
  };
}

function normalizeRegionalEvent(value: unknown): RegionalEvent | null {
  const event = normalizeEvent(value);
  return event ? { ...event, geometry: regionalGeometry(event.geometry) } : null;
}

function normalizeDriveBCEvidence(value: unknown, event: RegionalEvent): DriveBCAnalysisFinding['source_evidence'] {
  const evidence = isRecord(value) ? value : {};
  return {
    event_type: typeof evidence.event_type === 'string' ? evidence.event_type : event.event_type,
    status: nullableText(evidence.status),
    severity: nullableText(evidence.severity),
    event_subtypes: Array.isArray(evidence.event_subtypes) ? evidence.event_subtypes : [],
    roads: Array.isArray(evidence.roads) ? evidence.roads.filter(isRecord) : [],
    schedule: evidence.schedule ?? null,
    schedule_text: nullableText(evidence.schedule_text),
    direction_assessment: typeof evidence.direction_assessment === 'string' ? evidence.direction_assessment : 'undetermined',
    temporal_applicability: typeof evidence.temporal_applicability === 'string' ? evidence.temporal_applicability : 'unknown',
    current_impact: typeof evidence.current_impact === 'string' ? evidence.current_impact : 'not_established',
  };
}

function normalizeDetail(value: unknown, event: CityEvent) {
  const detail = isRecord(value) ? value : {};
  const availabilities = ['available', 'no_supported_fields', 'unavailable', 'parse_failed'] as const;
  const availability = availabilities.includes(detail.availability as (typeof availabilities)[number])
    ? detail.availability as (typeof availabilities)[number]
    : 'unavailable';
  return {
    event_id: event.id,
    source_url: nullableText(detail.source_url) ?? event.source_url,
    availability,
    title: nullableText(detail.title),
    location: nullableText(detail.location),
    description: nullableText(detail.description),
    status: nullableText(detail.status),
    schedule_text: nullableText(detail.schedule_text),
    restriction_text: nullableText(detail.restriction_text),
    exceptions: nullableText(detail.exceptions),
    posted_text: nullableText(detail.posted_text),
    updated_text: nullableText(detail.updated_text),
    retrieved_at: nullableText(detail.retrieved_at),
    from_cache: detail.from_cache === true,
    stale: detail.stale === true,
    error: nullableText(detail.error) as AnalysisFinding['detail']['error'],
  };
}

export function normalizeJourneyAnalysis(value: unknown): JourneyAnalysis | null {
  if (!isRecord(value) || !['available', 'partial', 'unavailable'].includes(String(value.status)) ||
      !Array.isArray(value.findings) || typeof value.summary !== 'string' || typeof value.analyzed_at !== 'string') return null;
  const trip = isRecord(value.trip) ? value.trip : null;
  const route = trip && isRecord(trip.selected_route) ? trip.selected_route : null;
  const origin = trip && isRecord(trip.origin) ? trip.origin : null;
  const destination = trip && isRecord(trip.destination) ? trip.destination : null;
  if (!trip || !route || !origin || !destination || trip.mode !== 'drive' ||
      typeof route.candidate_id !== 'string' || !isRecord(route.geometry) ||
      !Array.isArray(value.source_statuses) || value.source_statuses.length === 0) return null;
  const sourceStatuses = value.source_statuses.filter(isRecord).map((status) => ({
    source: typeof status.source === 'string' ? status.source : 'City of Vancouver Road Ahead',
    dataset_id: typeof status.dataset_id === 'string' ? status.dataset_id : 'unknown',
    success: status.success === true,
    available: status.available === true,
    fetched_at: nullableText(status.fetched_at),
    cache_hit: status.cache_hit === true,
    refreshed: status.refreshed === true,
    stale: status.stale === true,
    cache_age_seconds: typeof status.cache_age_seconds === 'number' && Number.isFinite(status.cache_age_seconds) ? status.cache_age_seconds : null,
    error: nullableText(status.error),
    records_received: typeof status.records_received === 'number' ? status.records_received : 0,
    records_normalized: typeof status.records_normalized === 'number' ? status.records_normalized : 0,
    records_skipped: typeof status.records_skipped === 'number' ? status.records_skipped : 0,
  }));
  const findings = value.findings.flatMap((item) => {
    if (!isRecord(item) || (item.classification !== 'direct_overlap' && item.classification !== 'nearby') ||
        typeof item.distance_meters !== 'number' || !Number.isFinite(item.distance_meters)) return [];
    const event = normalizeEvent(item.event);
    if (!event) return [];
    const classification = item.classification as AnalysisFinding['classification'];
    return [{ event, classification, distance_meters: item.distance_meters, detail: normalizeDetail(item.detail, event) }];
  });
  const unmatchableReasons = ['missing_geometry', 'invalid_structure', 'empty_geometry', 'invalid_topology', 'projection_failure'] as const;
  const unmatchableEvents = Array.isArray(value.unmatchable_events)
    ? value.unmatchable_events.filter((item) => isRecord(item) && typeof item.event_id === 'string' && unmatchableReasons.includes(item.reason as (typeof unmatchableReasons)[number]))
      .map((item) => ({ event_id: (item as Record<string, unknown>).event_id as string, reason: (item as Record<string, unknown>).reason as JourneyAnalysis['unmatchable_events'][number]['reason'] }))
    : [];
  const drivebcFindings: DriveBCAnalysisFinding[] = Array.isArray(value.drivebc_findings)
    ? value.drivebc_findings.flatMap((item) => {
      if (!isRecord(item) || (item.classification !== 'direct_overlap' && item.classification !== 'nearby') ||
          !['linestring_intersection', 'linestring_proximity', 'point_proximity'].includes(String(item.geometry_basis)) ||
          typeof item.distance_meters !== 'number' || !Number.isFinite(item.distance_meters)) return [];
      const event = normalizeRegionalEvent(item.event);
      if (!event || !event.geometry) return [];
      return [{
        event,
        classification: item.classification,
        distance_meters: item.distance_meters,
        geometry_basis: item.geometry_basis as DriveBCGeometryBasis,
        enrichment_applicability: typeof item.enrichment_applicability === 'string' ? item.enrichment_applicability : 'not_applicable',
        source_evidence: normalizeDriveBCEvidence(item.source_evidence, event),
      }];
    }) : [];
  const regionalEvents = Array.isArray(value.regional_events)
    ? value.regional_events.flatMap((item) => { const event = normalizeRegionalEvent(item); return event ? [event] : []; })
    : [];
  const normalizedTrip: JourneyAnalysis['trip'] = {
    origin: origin as unknown as JourneyAnalysis['trip']['origin'],
    destination: destination as unknown as JourneyAnalysis['trip']['destination'],
    mode: 'drive',
    selected_route: {
      candidate_id: route.candidate_id,
      geometry: route.geometry as unknown as JourneyAnalysis['trip']['selected_route']['geometry'],
      distance_meters: typeof route.distance_meters === 'number' ? route.distance_meters : 0,
      duration_seconds: typeof route.duration_seconds === 'number' ? route.duration_seconds : 0,
      label: nullableText(route.label),
    },
  };
  return {
    trip: normalizedTrip,
    status: value.status as JourneyAnalysis['status'],
    findings,
    drivebc_findings: drivebcFindings,
    regional_events: regionalEvents,
    unmatchable_events: unmatchableEvents,
    source_statuses: sourceStatuses,
    destination_weather: normalizeDestinationWeather(value.destination_weather),
    summary: value.summary,
    analyzed_at: value.analyzed_at,
  };
}

export function officialDetailUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) && url.hostname.toLowerCase() === 'vanmapp1.vancouver.ca' &&
      (url.port === '' || (url.protocol === 'http:' && url.port === '80') || (url.protocol === 'https:' && url.port === '443')) &&
      /^\/roadahead\/events\/details\/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\/?$/i.test(url.pathname) &&
      !url.username && !url.password && !url.search && !url.hash
      ? url.toString()
      : null;
  } catch {
    return null;
  }
}

export function officialDetailLinkLabel(availability: AnalysisFinding['detail']['availability']): string {
  return availability === 'unavailable' || availability === 'parse_failed'
    ? 'Open official Road Ahead detail (page may not be accessible) ↗'
    : 'Open official Road Ahead detail ↗';
}

export function formatAge(seconds: number | null): string | null {
  if (seconds === null || !Number.isFinite(seconds) || seconds < 0) return null;
  const hours = Math.floor(seconds / 3600);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d ${hours % 24}h old`;
  if (hours > 0) return `${hours}h old`;
  if (seconds < 60) return 'under 1m old';
  return `${Math.max(1, Math.floor(seconds / 60))}m old`;
}

export function eventTitle(finding: AnalysisFinding): string {
  return finding.detail.title ?? finding.event.title;
}

export function eventDescription(finding: AnalysisFinding): string | null {
  return finding.detail.description ?? finding.event.description;
}

export function eventTypeLabel(finding: AnalysisFinding): string {
  if (finding.event.event_type === 'road_closure') return 'Road closure record';
  if (finding.event.event_type === 'construction') return 'Construction project';
  return finding.event.event_type.replaceAll('_', ' ');
}
