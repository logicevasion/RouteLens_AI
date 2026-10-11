import type { Location } from './locationTypes';
import type { RouteLineString } from './routeTypes';

export type AnalysisStatus = 'available' | 'partial' | 'unavailable';
export type FindingClassification = 'direct_overlap' | 'nearby';
export type RoadAheadGeometry =
  | { type: 'LineString'; coordinates: number[][] }
  | { type: 'MultiLineString'; coordinates: number[][][] }
  | { type: 'Polygon'; coordinates: number[][][] }
  | { type: 'GeometryCollection'; geometries: RoadAheadGeometry[] };

export type SelectedRoute = {
  candidate_id: string;
  geometry: RouteLineString;
  distance_meters: number;
  duration_seconds: number;
  label?: string | null;
};

export type AnalysisRequest = {
  origin: Location;
  destination: Location;
  mode: 'drive';
  selected_route: SelectedRoute;
};

export type CityEvent = {
  id: string;
  source: string;
  source_dataset_id: string;
  source_record_id: string;
  event_type: string;
  title: string;
  description: string | null;
  geometry: RoadAheadGeometry | null;
  latitude: number | null;
  longitude: number | null;
  severity: string | null;
  status: string | null;
  schedule_text: string | null;
  restriction_text: string | null;
  observed_at: string | null;
  updated_at: string | null;
  source_url: string | null;
  relevance_reason: string | null;
  source_metadata: Record<string, unknown>;
  attribution: string;
};

export type DetailEnrichment = {
  event_id: string;
  source_url: string | null;
  availability: 'available' | 'no_supported_fields' | 'unavailable' | 'parse_failed';
  title: string | null;
  location: string | null;
  description: string | null;
  status: string | null;
  schedule_text: string | null;
  restriction_text: string | null;
  exceptions: string | null;
  posted_text: string | null;
  updated_text: string | null;
  retrieved_at: string | null;
  from_cache: boolean;
  stale: boolean;
  error: 'invalid_source_url' | 'http_failure' | 'timeout' | 'invalid_content' | 'parse_failure' | null;
};

export type AnalysisFinding = {
  event: CityEvent;
  classification: FindingClassification;
  distance_meters: number;
  detail: DetailEnrichment;
};

export type SourceStatus = {
  source: string;
  dataset_id: string;
  success: boolean;
  available: boolean;
  fetched_at: string | null;
  cache_hit: boolean;
  refreshed: boolean;
  stale: boolean;
  cache_age_seconds: number | null;
  error: string | null;
  records_received: number;
  records_normalized: number;
  records_skipped: number;
};

export type UnmatchableEvent = {
  event_id: string;
  reason: 'missing_geometry' | 'invalid_structure' | 'empty_geometry' | 'invalid_topology' | 'projection_failure';
};

export type JourneyAnalysis = {
  trip: AnalysisRequest;
  status: AnalysisStatus;
  findings: AnalysisFinding[];
  unmatchable_events: UnmatchableEvent[];
  source_statuses: SourceStatus[];
  summary: string;
  analyzed_at: string;
};

export type AnalysisState =
  | { status: 'idle'; result: null; error: null }
  | { status: 'loading'; result: null; error: null }
  | { status: 'success'; result: JourneyAnalysis; error: null }
  | { status: 'error'; result: null; error: string };
