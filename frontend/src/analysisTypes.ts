import type { Location } from './locationTypes';
import type { RouteLineString } from './routeTypes';

export type AnalysisStatus = 'available' | 'partial' | 'unavailable';
export type FindingClassification = 'direct_overlap' | 'nearby';
export type RoadAheadGeometry =
  | { type: 'Point'; coordinates: number[] }
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

export type DriveBCGeometryBasis = 'linestring_intersection' | 'linestring_proximity' | 'point_proximity';
export type RegionalGeometry =
  | { type: 'Point'; coordinates: number[] }
  | { type: 'LineString'; coordinates: number[][] };
export type DriveBCSourceEvidence = {
  event_type: string;
  status: string | null;
  severity: string | null;
  event_subtypes: unknown[];
  roads: Record<string, unknown>[];
  schedule: unknown;
  schedule_text: string | null;
  direction_assessment: string;
  temporal_applicability: string;
  current_impact: string;
};
export type DriveBCAnalysisFinding = {
  event: Omit<CityEvent, 'geometry'> & { geometry: RegionalGeometry | null };
  classification: FindingClassification;
  distance_meters: number;
  geometry_basis: DriveBCGeometryBasis;
  enrichment_applicability: string;
  source_evidence: DriveBCSourceEvidence;
};
export type RegionalEvent = Omit<CityEvent, 'geometry'> & { geometry: RegionalGeometry | null };

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

export type WeatherSourceStatus = Omit<SourceStatus, 'records_received' | 'records_normalized' | 'records_skipped'>;
export type WeatherCondition = { code: number | null; group: string | null; description: string | null };
export type CurrentWeatherEvidence = {
  source: string; product: string; observed_at: string; fetched_at: string;
  temperature_c: number | null; feels_like_c: number | null; condition: WeatherCondition | null;
  humidity_pct: number | null; wind_speed_m_s: number | null; wind_direction_deg: number | null;
  wind_gust_m_s: number | null; visibility_m: number | null;
};
export type ForecastInterval = {
  source: string; product: string; forecast_at: string; fetched_at: string;
  precipitation_probability_pct: number | null; temperature_c: number | null;
  feels_like_c: number | null; condition: WeatherCondition | null;
  humidity_pct: number | null; wind_speed_m_s: number | null; visibility_m: number | null;
};
export type ForecastCoverage = {
  evaluation_time: string; window_end: string; first_interval_at: string | null;
  last_interval_at: string | null; expected_interval_count: number; returned_interval_count: number;
  missing_intervals: string[]; malformed_records: number; duplicate_records: number;
  initial_page_only: boolean; continuous: boolean;
};
export type MeasuredValue = {
  value: number; unit: string; source_field: string; interval_seconds: number | null;
  quality_code: number | null;
};
export type StationObservation = {
  source: string; station_id: string; station_name: string | null; latitude: number | null;
  longitude: number | null; observed_at: string; retrieved_at: string;
  temperature: MeasuredValue | null; relative_humidity: MeasuredValue | null;
  precipitation: MeasuredValue[]; wind_speed: MeasuredValue | null;
  wind_direction: MeasuredValue | null; snow_depth: MeasuredValue | null; attribution: string;
};
export type SelectedStationObservation = {
  observation: StationObservation; distance_meters: number; observation_age_seconds: number;
  observation_stale: boolean; cache_stale: boolean; useful_measurements: string[];
  selection_reason: string;
};
export type DestinationWeather = {
  openweather_current: { weather: CurrentWeatherEvidence | null; status: WeatherSourceStatus };
  openweather_forecast: { intervals: ForecastInterval[]; coverage: ForecastCoverage | null; status: WeatherSourceStatus };
  eccc_status: WeatherSourceStatus; eccc_observations: SelectedStationObservation[];
  eccc_attribution: string;
};

export type UnmatchableEvent = {
  event_id: string;
  reason: 'missing_geometry' | 'invalid_structure' | 'empty_geometry' | 'invalid_topology' | 'projection_failure';
};

export type JourneyAnalysis = {
  trip: AnalysisRequest;
  status: AnalysisStatus;
  findings: AnalysisFinding[];
  drivebc_findings: DriveBCAnalysisFinding[];
  regional_events: RegionalEvent[];
  unmatchable_events: UnmatchableEvent[];
  source_statuses: SourceStatus[];
  destination_weather: DestinationWeather;
  summary: string;
  analyzed_at: string;
};

export type AnalysisState =
  | { status: 'idle'; result: null; error: null }
  | { status: 'loading'; result: null; error: null }
  | { status: 'success'; result: JourneyAnalysis; error: null }
  | { status: 'error'; result: null; error: string };
