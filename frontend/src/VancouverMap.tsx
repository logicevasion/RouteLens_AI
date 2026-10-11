import { useEffect, useRef, useState } from 'react';
import {
  AttributionControl,
  LngLatBounds,
  Map as MapLibreMap,
  NavigationControl,
  setWorkerUrl,
  type ErrorEvent,
  type GeoJSONSource,
  type Map as MapLibreMapType,
} from 'maplibre-gl';
import type { FeatureCollection, LineString } from 'geojson';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';
import { routeColor, type RouteCandidate } from './routeTypes';
import type { AnalysisFinding, DriveBCAnalysisFinding, RegionalEvent } from './analysisTypes';
import { eventBounds, regionalEventsGeoJson, roadAheadGeoJson, sourceScopedEventId, type RoadAheadFeatureCollection } from './roadAhead';

type MapStatus = 'loading' | 'ready' | 'error';
type RouteProperties = { routeId: string; selected: boolean; color: string };
type RouteFeatureCollection = FeatureCollection<LineString, RouteProperties>;
type VancouverMapProps = {
  routes: RouteCandidate[];
  selectedRouteId: string | null;
  fitKey: number;
  findings: AnalysisFinding[];
  drivebcFindings: DriveBCAnalysisFinding[];
  regionalEvents: RegionalEvent[];
  selectedEventId: string | null;
  onSelectEvent: (eventId: string) => void;
};

const vancouverCenter: [number, number] = [-123.1207, 49.2827];
const styleUrl = 'https://api.maptiler.com/maps/streets-v4-dark/style.json';
const routeSourceId = 'routelens-routes';
const roadAheadSourceId = 'routelens-road-ahead';
const regionalSourceId = 'routelens-drivebc-regional';

setWorkerUrl(maplibreWorkerUrl);

function createStyleUrl(apiKey: string): string {
  const url = new URL(styleUrl);
  url.searchParams.set('key', apiKey);
  return url.toString();
}

function safeDiagnostic(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  return message.replace(/https?:\/\/\S+/gi, '[resource URL]').replace(/([?&]key=)[^&\s]+/gi, '$1[redacted]');
}

function routeData(routes: RouteCandidate[], selectedRouteId: string | null): RouteFeatureCollection {
  return {
    type: 'FeatureCollection',
    features: routes.map((route) => ({
      type: 'Feature',
      id: route.id,
      properties: { routeId: route.id, selected: route.id === selectedRouteId, color: routeColor(route.id) },
      geometry: route.geometry,
    })),
  };
}

function syncRoutes(
  map: MapLibreMapType,
  routes: RouteCandidate[],
  selectedRouteId: string | null,
  fitKey: number,
  lastFitKey: { current: number },
) {
  const data = routeData(routes, selectedRouteId);
  const source = map.getSource(routeSourceId);
  if (source?.type === 'geojson') (source as GeoJSONSource).setData(data);
  else if (!source) map.addSource(routeSourceId, { type: 'geojson', data });

  if (!map.getLayer('routelens-route-unselected')) {
    map.addLayer({
      id: 'routelens-route-unselected', type: 'line', source: routeSourceId,
      filter: ['==', ['get', 'selected'], false],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': ['get', 'color'], 'line-width': 3, 'line-opacity': 0.72 },
    });
  }
  if (!map.getLayer('routelens-route-selected-casing')) {
    map.addLayer({
      id: 'routelens-route-selected-casing', type: 'line', source: routeSourceId,
      filter: ['==', ['get', 'selected'], true],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#08151a', 'line-width': 9, 'line-opacity': 0.88 },
    });
  }
  if (!map.getLayer('routelens-route-selected')) {
    map.addLayer({
      id: 'routelens-route-selected', type: 'line', source: routeSourceId,
      filter: ['==', ['get', 'selected'], true],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#51d5cc', 'line-width': 5.5, 'line-opacity': 1 },
    });
  }

  if (routes.length > 0 && fitKey !== lastFitKey.current) {
    const bounds = new LngLatBounds();
    for (const route of routes) {
      for (const coordinate of route.geometry.coordinates) bounds.extend(coordinate);
    }
    lastFitKey.current = fitKey;
    if (!bounds.isEmpty()) {
      map.fitBounds(bounds, {
        padding: { top: 74, right: 64, bottom: 56, left: 64 },
        maxZoom: 14,
        duration: 650,
      });
    }
  }
}

function ensureRoadAheadLayers(map: MapLibreMapType) {
  if (!map.getLayer('routelens-road-ahead-fill')) {
    map.addLayer({
      id: 'routelens-road-ahead-fill', type: 'fill', source: roadAheadSourceId,
      filter: ['!=', ['get', 'selected'], true],
      paint: {
        'fill-color': ['case', ['==', ['get', 'classification'], 'direct_overlap'], '#ee7966', '#e5ba70'],
        'fill-opacity': ['case', ['==', ['get', 'classification'], 'direct_overlap'], 0.19, 0.11],
      },
    }, map.getLayer('routelens-route-selected-casing') ? 'routelens-route-selected-casing' : undefined);
  }
  if (!map.getLayer('routelens-road-ahead-line')) {
    map.addLayer({
      id: 'routelens-road-ahead-line', type: 'line', source: roadAheadSourceId,
      filter: ['!=', ['get', 'selected'], true],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: {
        'line-color': ['case', ['==', ['get', 'classification'], 'direct_overlap'], '#ee7966', '#e5ba70'],
        'line-width': ['case', ['==', ['get', 'classification'], 'direct_overlap'], 3.5, 2.5],
        'line-opacity': ['case', ['==', ['get', 'classification'], 'direct_overlap'], 0.88, 0.7],
      },
    }, map.getLayer('routelens-route-selected-casing') ? 'routelens-route-selected-casing' : undefined);
  }
  if (!map.getLayer('routelens-road-ahead-selected-fill')) {
    map.addLayer({
      id: 'routelens-road-ahead-selected-fill', type: 'fill', source: roadAheadSourceId,
      filter: ['==', ['get', 'selected'], true],
      paint: { 'fill-color': '#fff06a', 'fill-opacity': 0.12 },
    });
  }
  if (!map.getLayer('routelens-road-ahead-selected-casing')) {
    map.addLayer({
      id: 'routelens-road-ahead-selected-casing', type: 'line', source: roadAheadSourceId,
      filter: ['==', ['get', 'selected'], true],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#17242b', 'line-width': 12, 'line-opacity': 0.96 },
    });
  }
  if (!map.getLayer('routelens-road-ahead-selected-line')) {
    map.addLayer({
      id: 'routelens-road-ahead-selected-line', type: 'line', source: roadAheadSourceId,
      filter: ['==', ['get', 'selected'], true],
      layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-color': '#fff06a', 'line-width': 7, 'line-opacity': 1 },
    });
  }
}

function syncRoadAhead(
  map: MapLibreMapType,
  findings: AnalysisFinding[],
  selectedEventId: string | null,
) {
  const data = roadAheadGeoJson(findings, selectedEventId) as RoadAheadFeatureCollection;
  const source = map.getSource(roadAheadSourceId);
  if (source?.type === 'geojson') (source as GeoJSONSource).setData(data);
  else if (!source) map.addSource(roadAheadSourceId, { type: 'geojson', data });
  ensureRoadAheadLayers(map);
  for (const layer of ['routelens-drivebc-selected-line-casing', 'routelens-drivebc-selected-line', 'routelens-drivebc-selected-point']) {
    if (map.getLayer(layer)) map.moveLayer(layer);
  }
}

function syncRegional(map: MapLibreMapType, events: RegionalEvent[], selectedEventId: string | null) {
  const data = regionalEventsGeoJson(events, selectedEventId);
  const source = map.getSource(regionalSourceId);
  if (source?.type === 'geojson') (source as GeoJSONSource).setData(data);
  else if (!source) map.addSource(regionalSourceId, { type: 'geojson', data });
  const before = map.getLayer('routelens-route-selected-casing') ? 'routelens-route-selected-casing' : undefined;
  if (!map.getLayer('routelens-drivebc-lines')) map.addLayer({
    id: 'routelens-drivebc-lines', type: 'line', source: regionalSourceId,
    filter: ['all', ['==', ['geometry-type'], 'LineString'], ['!=', ['get', 'selected'], true]],
    layout: { 'line-cap': 'round', 'line-join': 'round' },
    paint: { 'line-color': '#8c9cae', 'line-width': 2.2, 'line-opacity': 0.48, 'line-dasharray': [2, 1.5] },
  }, before);
  if (!map.getLayer('routelens-drivebc-points')) map.addLayer({
    id: 'routelens-drivebc-points', type: 'circle', source: regionalSourceId,
    filter: ['all', ['==', ['geometry-type'], 'Point'], ['!=', ['get', 'selected'], true]],
    paint: { 'circle-radius': 4, 'circle-color': '#8099b0', 'circle-opacity': 0.78, 'circle-stroke-color': '#17242b', 'circle-stroke-width': 1.2 },
  }, before);
  if (!map.getLayer('routelens-drivebc-selected-line-casing')) map.addLayer({
    id: 'routelens-drivebc-selected-line-casing', type: 'line', source: regionalSourceId,
    filter: ['all', ['==', ['geometry-type'], 'LineString'], ['==', ['get', 'selected'], true]],
    layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#10232d', 'line-width': 9, 'line-opacity': 0.95 },
  });
  if (!map.getLayer('routelens-drivebc-selected-line')) map.addLayer({
    id: 'routelens-drivebc-selected-line', type: 'line', source: regionalSourceId,
    filter: ['all', ['==', ['geometry-type'], 'LineString'], ['==', ['get', 'selected'], true]],
    layout: { 'line-cap': 'round', 'line-join': 'round' }, paint: { 'line-color': '#fff06a', 'line-width': 5.5, 'line-opacity': 1 },
  });
  if (!map.getLayer('routelens-drivebc-selected-point')) map.addLayer({
    id: 'routelens-drivebc-selected-point', type: 'circle', source: regionalSourceId,
    filter: ['all', ['==', ['geometry-type'], 'Point'], ['==', ['get', 'selected'], true]],
    paint: { 'circle-radius': 8, 'circle-color': '#fff06a', 'circle-stroke-color': '#10232d', 'circle-stroke-width': 2.5 },
  });
}

function focusSelectedEvent(map: MapLibreMapType, findings: AnalysisFinding[], drivebc: DriveBCAnalysisFinding[], events: RegionalEvent[], selectedEventId: string | null) {
  if (!selectedEventId) return;
  const event = findings.find((item) => sourceScopedEventId(item.event) === selectedEventId)?.event ??
    drivebc.find((item) => sourceScopedEventId(item.event) === selectedEventId)?.event ??
    events.find((item) => sourceScopedEventId(item) === selectedEventId);
  const bounds = event ? eventBounds(event.geometry) : null;
  if (!bounds) return;
  if (bounds[0][0] === bounds[1][0] && bounds[0][1] === bounds[1][1]) {
    map.easeTo({ center: bounds[0], zoom: Math.min(15.5, Math.max(map.getZoom(), 14)), duration: 450, padding: { top: 70, right: 70, bottom: 70, left: 70 } });
  } else map.fitBounds(new LngLatBounds(bounds[0], bounds[1]), { padding: 84, maxZoom: 15.5, duration: 450 });
}

export default function VancouverMap({ routes, selectedRouteId, fitKey, findings, drivebcFindings, regionalEvents, selectedEventId, onSelectEvent }: VancouverMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMapType | null>(null);
  const lastFitKey = useRef(0);
  const routeProps = useRef({ routes, selectedRouteId, fitKey, findings, drivebcFindings, regionalEvents, selectedEventId, onSelectEvent });
  routeProps.current = { routes, selectedRouteId, fitKey, findings, drivebcFindings, regionalEvents, selectedEventId, onSelectEvent };
  const [status, setStatus] = useState<MapStatus>('loading');
  const apiKey = import.meta.env.VITE_MAPTILER_API_KEY?.trim();

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !apiKey) return;

    let map: MapLibreMap;
    try {
      map = new MapLibreMap({
        container,
        style: createStyleUrl(apiKey),
        center: vancouverCenter,
        zoom: 12,
        attributionControl: false,
        trackResize: true,
      });
    } catch (error) {
      container.replaceChildren();
      setStatus('error');
      if (import.meta.env.DEV) console.error('RouteLens could not initialize MapLibre.', safeDiagnostic(error));
      return;
    }
    mapRef.current = map;
    map.addControl(new AttributionControl({ compact: false }), 'bottom-right');
    map.addControl(new NavigationControl({ showCompass: true }), 'top-right');

    let sawResourceError = false;
    let failureTimer: ReturnType<typeof setTimeout> | undefined;
    const handleLoad = () => {
      if (failureTimer) clearTimeout(failureTimer);
      failureTimer = undefined;
      setStatus('ready');
      const current = routeProps.current;
      syncRoutes(map, current.routes, current.selectedRouteId, current.fitKey, lastFitKey);
      syncRegional(map, current.regionalEvents, current.selectedEventId);
      syncRoadAhead(map, current.findings, current.selectedEventId);
      focusSelectedEvent(map, current.findings, current.drivebcFindings, current.regionalEvents, current.selectedEventId);
      const selectRegionalFeature = (event: { features?: Array<{ properties?: Record<string, unknown> }> }) => {
        const id = event.features?.[0]?.properties?.eventId;
        if (typeof id === 'string') routeProps.current.onSelectEvent(id);
      };
      map.on('click', 'routelens-drivebc-points', selectRegionalFeature);
      map.on('click', 'routelens-drivebc-lines', selectRegionalFeature);
      map.once('remove', () => {
        map.off('click', 'routelens-drivebc-points', selectRegionalFeature);
        map.off('click', 'routelens-drivebc-lines', selectRegionalFeature);
      });
    };
    const handleError = (event: ErrorEvent) => {
      sawResourceError = true;
      if (!failureTimer) {
        failureTimer = setTimeout(() => {
          if (map.loaded()) return;
          setStatus('error');
          if (import.meta.env.DEV && sawResourceError) {
            console.error('RouteLens map resources failed to load. Check MapTiler connectivity and MAPTILER_API_KEY.', safeDiagnostic(event.error));
          }
        }, 10000);
      }
    };

    map.once('load', handleLoad);
    map.on('error', handleError);
    const resizeObserver = new ResizeObserver(() => map.resize());
    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      map.off('load', handleLoad);
      map.off('error', handleError);
      if (failureTimer) clearTimeout(failureTimer);
      map.remove();
      mapRef.current = null;
    };
  }, [apiKey]);

  // Keep the map instance stable while route data and selection change.
  useEffect(() => {
    const map = mapRef.current;
    if (map?.isStyleLoaded()) syncRoutes(map, routes, selectedRouteId, fitKey, lastFitKey);
  }, [routes, selectedRouteId, fitKey]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map?.isStyleLoaded()) return;
    syncRegional(map, regionalEvents, selectedEventId);
    syncRoadAhead(map, findings, selectedEventId);
  }, [findings, regionalEvents, selectedEventId]);

  useEffect(() => {
    const map = mapRef.current;
    if (map?.isStyleLoaded()) focusSelectedEvent(map, routeProps.current.findings, routeProps.current.drivebcFindings, routeProps.current.regionalEvents, selectedEventId);
  }, [selectedEventId]);

  return (
    <section className="map-frame" aria-label="Interactive map of Vancouver">
      <div className="map-canvas" ref={containerRef} />
      {status === 'ready' && <div className="map-legend" aria-label="Map layers">
        <span><i className="legend-route" />Selected route</span><span><i className="legend-road-ahead-direct" />Road Ahead intersection</span><span><i className="legend-road-ahead-nearby" />Road Ahead nearby</span>
        <span><i className="legend-drivebc-point" />DriveBC regional Point</span><span><i className="legend-drivebc-line" />DriveBC regional LineString</span>
        <span><i className="legend-selected-event" />Focused event</span>
      </div>}
      {!apiKey ? (
        <div className="map-message" role="status">
          <h2>Map configuration required</h2>
          <p>Add <code>MAPTILER_API_KEY</code> to the project root <code>.env</code>, then restart the Vite server.</p>
        </div>
      ) : status === 'loading' ? (
        <div className="map-message map-message-loading" role="status" aria-live="polite">
          <span className="map-spinner" aria-hidden="true" /><span>Loading Vancouver map…</span>
        </div>
      ) : status === 'error' ? (
        <div className="map-message" role="alert">
          <h2>Map unavailable</h2>
          <p>MapTiler could not load the Vancouver basemap. Check the connection and map key.</p>
          {import.meta.env.DEV && <p className="map-diagnostic">Development hint: verify MAPTILER_API_KEY in the root .env.</p>}
        </div>
      ) : null}
    </section>
  );
}
