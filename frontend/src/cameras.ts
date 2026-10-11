import type { Location } from './locationTypes';

export type CameraView = {
  view_id: string;
  direction_label: string | null;
  image_reference: string;
  retrieved_at: string;
  source_capture_at: string | null;
  cache_age_seconds: number;
  stale: boolean;
  width: number;
  height: number;
  content_type: string;
};

export type DestinationCamera = {
  destination: Location;
  status: 'available' | 'stale' | 'unavailable';
  intersection: {
    intersection_id: string;
    name: string;
    latitude: number;
    longitude: number;
    distance_metres: number;
    distance_is_approximate: boolean;
    official_page_url: string;
    source: string;
    attribution: string;
  } | null;
  views: CameraView[];
  stale_views: CameraView[];
  diagnostics: {
    candidates_attempted: number;
    views_attempted: number;
    views_succeeded: number;
    views_failed: number;
    fallback_used: boolean;
    catalogue_stale: boolean;
    failures: { view_id: string; error_code: string }[];
  };
};

export type CameraState =
  | { status: 'idle' }
  | { status: 'loading'; requestKey: string }
  | { status: 'success'; requestKey: string; result: DestinationCamera }
  | { status: 'error'; requestKey: string };

type RecordValue = Record<string, unknown>;
const isRecord = (value: unknown): value is RecordValue => typeof value === 'object' && value !== null && !Array.isArray(value);
const isText = (value: unknown): value is string => typeof value === 'string' && value.trim().length > 0;
const isFiniteNumber = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value);

function normalizeLocation(value: unknown): Location | null {
  if (!isRecord(value) || !isText(value.name) || !isFiniteNumber(value.latitude) || !isFiniteNumber(value.longitude)) return null;
  if (value.latitude < -90 || value.latitude > 90 || value.longitude < -180 || value.longitude > 180) return null;
  return { name: value.name, latitude: value.latitude, longitude: value.longitude };
}

function normalizeView(value: unknown): CameraView | null {
  if (!isRecord(value) || !isText(value.view_id) || !isText(value.image_reference) ||
      !/^\/api\/cameras\/images\/[a-f0-9]{32}$/.test(value.image_reference) ||
      !(value.direction_label === null || typeof value.direction_label === 'string') ||
      !isText(value.retrieved_at) || !(value.source_capture_at === null || typeof value.source_capture_at === 'string') ||
      !isFiniteNumber(value.cache_age_seconds) || value.cache_age_seconds < 0 ||
      typeof value.stale !== 'boolean' || !Number.isInteger(value.width) || (value.width as number) <= 0 ||
      !Number.isInteger(value.height) || (value.height as number) <= 0 ||
      !['image/jpeg', 'image/png', 'image/webp'].includes(String(value.content_type))) return null;
  return value as CameraView;
}

function normalizeIntersection(value: unknown): DestinationCamera['intersection'] {
  if (!isRecord(value) || !isText(value.intersection_id) || !isText(value.name) ||
      !isFiniteNumber(value.latitude) || value.latitude < -90 || value.latitude > 90 ||
      !isFiniteNumber(value.longitude) || value.longitude < -180 || value.longitude > 180 ||
      !isFiniteNumber(value.distance_metres) || value.distance_metres < 0 ||
      typeof value.distance_is_approximate !== 'boolean' || !isText(value.official_page_url) ||
      typeof value.source !== 'string' || typeof value.attribution !== 'string') return null;
  let sourceUrl: URL;
  try { sourceUrl = new URL(value.official_page_url); } catch { return null; }
  if (sourceUrl.protocol !== 'https:' || sourceUrl.hostname !== 'trafficcams.vancouver.ca' || sourceUrl.username || sourceUrl.password) return null;
  return { ...value, official_page_url: sourceUrl.href } as DestinationCamera['intersection'];
}

export function normalizeDestinationCamera(value: unknown): DestinationCamera | null {
  if (!isRecord(value)) return null;
  const destination = normalizeLocation(value.destination);
  if (!destination || !['available', 'stale', 'unavailable'].includes(String(value.status))) return null;
  const status = value.status as DestinationCamera['status'];
  if (!isRecord(value.diagnostics)) return null;
  const diagnostics = value.diagnostics;
  const numberKeys = ['candidates_attempted', 'views_attempted', 'views_succeeded', 'views_failed'] as const;
  if (numberKeys.some((key) => !Number.isInteger(diagnostics[key]) || (diagnostics[key] as number) < 0) ||
      typeof diagnostics.fallback_used !== 'boolean' || typeof diagnostics.catalogue_stale !== 'boolean' ||
      !Array.isArray(diagnostics.failures) || !diagnostics.failures.every((failure) => isRecord(failure) && isText(failure.view_id) && isText(failure.error_code))) return null;
  const intersection = value.intersection === null ? null : normalizeIntersection(value.intersection);
  if (value.intersection !== null && !intersection) return null;
  if (!Array.isArray(value.views) || !Array.isArray(value.stale_views)) return null;
  const views = value.views.map(normalizeView);
  const staleViews = value.stale_views.map(normalizeView);
  if (views.some((view) => !view) || staleViews.some((view) => !view)) return null;
  if (status === 'available' && (!intersection || views.length === 0) || status === 'stale' && (!intersection || staleViews.length === 0) || status === 'unavailable' && (intersection !== null || views.length || staleViews.length)) return null;
  return {
    destination, status, intersection, views: views as CameraView[], stale_views: staleViews as CameraView[],
    diagnostics: {
      candidates_attempted: diagnostics.candidates_attempted as number,
      views_attempted: diagnostics.views_attempted as number,
      views_succeeded: diagnostics.views_succeeded as number,
      views_failed: diagnostics.views_failed as number,
      fallback_used: diagnostics.fallback_used,
      catalogue_stale: diagnostics.catalogue_stale,
      failures: diagnostics.failures as DestinationCamera['diagnostics']['failures'],
    },
  };
}

export async function fetchDestinationCamera(destination: Location, signal: AbortSignal): Promise<DestinationCamera> {
  const response = await fetch('/api/cameras/nearest', {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ destination }), signal,
  });
  if (!response.ok) throw new Error('Camera service unavailable');
  const result = normalizeDestinationCamera(await response.json());
  if (!result || result.destination.latitude !== destination.latitude || result.destination.longitude !== destination.longitude) {
    throw new Error('Camera service returned an unreadable result');
  }
  return result;
}

export function isCurrentCameraRequest(requestKey: string, activeRequestKey: string | null, requestId: number, activeRequestId: number): boolean {
  return requestKey === activeRequestKey && requestId === activeRequestId;
}

export function isCurrentCameraImageEvent(imageRequestKey: string, activeRequestKey: string): boolean {
  return imageRequestKey === activeRequestKey;
}

export function handleCameraImageError(imageRequestKey: string, activeRequestKey: string, markUnavailable: () => void): void {
  if (isCurrentCameraImageEvent(imageRequestKey, activeRequestKey)) markUnavailable();
}

export function formatCameraAge(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  if (minutes < 1) return 'less than a minute ago';
  if (minutes < 60) return `about ${minutes} minute${minutes === 1 ? '' : 's'} ago`;
  const hours = Math.floor(minutes / 60);
  return `about ${hours} hour${hours === 1 ? '' : 's'} ago`;
}

export function formatRetrievedAt(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? 'time unavailable' : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' });
}
