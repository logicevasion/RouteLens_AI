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

type MapStatus = 'loading' | 'ready' | 'error';
type RouteProperties = { routeId: string; selected: boolean; color: string };
type RouteFeatureCollection = FeatureCollection<LineString, RouteProperties>;
type VancouverMapProps = { routes: RouteCandidate[]; selectedRouteId: string | null; fitKey: number };

const vancouverCenter: [number, number] = [-123.1207, 49.2827];
const styleUrl = 'https://api.maptiler.com/maps/streets-v4-dark/style.json';
const routeSourceId = 'routelens-routes';

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

export default function VancouverMap({ routes, selectedRouteId, fitKey }: VancouverMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMapType | null>(null);
  const lastFitKey = useRef(0);
  const routeProps = useRef({ routes, selectedRouteId, fitKey });
  routeProps.current = { routes, selectedRouteId, fitKey };
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

  return (
    <section className="map-frame" aria-label="Interactive map of Vancouver">
      <div className="map-canvas" ref={containerRef} />
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
