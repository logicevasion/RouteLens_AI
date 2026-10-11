import type { Location } from './locationTypes';

/** GeoJSON LineString coordinates are longitude, latitude pairs. */
export type RouteLineString = {
  type: 'LineString';
  coordinates: [number, number][];
};

/** RouteLens-owned driving candidate returned by the FastAPI routing API. */
export type RouteCandidate = {
  id: string;
  geometry: RouteLineString;
  distance_meters: number;
  duration_seconds: number;
  label?: string | null;
};

const alternativeColors = ['#8fb7cf', '#c7a96f', '#ad9bd4', '#79b8a8'];

/** Stable subdued color for distinguishing unselected route identities. */
export function routeColor(id: string): string {
  let hash = 0;
  for (const character of id) hash = (hash * 31 + character.charCodeAt(0)) >>> 0;
  return alternativeColors[hash % alternativeColors.length];
}

export type DrivingRoutesRequest = {
  origin: Location;
  destination: Location;
};

export type DrivingRoutesResponse = {
  routes: RouteCandidate[];
};

export type RoutingErrorCode =
  | 'unsupported_destination'
  | 'routing_not_configured'
  | 'routing_authentication_failed'
  | 'routing_rate_limited'
  | 'no_route_found'
  | 'routing_timeout'
  | 'routing_provider_unavailable';

export type RoutingApiError = {
  detail?: {
    code?: RoutingErrorCode | string;
    message?: string;
  };
};

export type RouteRequestState =
  | { status: 'idle'; candidates: []; selectedRoute: null; error: null; fitKey: number }
  | { status: 'loading'; candidates: []; selectedRoute: null; error: null; fitKey: number }
  | { status: 'ready'; candidates: RouteCandidate[]; selectedRoute: RouteCandidate | null; error: null; fitKey: number }
  | { status: 'empty'; candidates: []; selectedRoute: null; error: null; fitKey: number }
  | { status: 'error'; candidates: []; selectedRoute: null; error: string; fitKey: number };
