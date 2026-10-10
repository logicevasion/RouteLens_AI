import { useEffect, useRef, useState } from 'react';
import {
  AttributionControl,
  Map as MapLibreMap,
  NavigationControl,
  setWorkerUrl,
  type ErrorEvent,
} from 'maplibre-gl';
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url';

type MapStatus = 'loading' | 'ready' | 'error';

const vancouverCenter: [number, number] = [-123.1207, 49.2827];
const styleUrl = 'https://api.maptiler.com/maps/streets-v4-dark/style.json';

setWorkerUrl(maplibreWorkerUrl);

function createStyleUrl(apiKey: string): string {
  const url = new URL(styleUrl);
  url.searchParams.set('key', apiKey);
  return url.toString();
}

function safeDiagnostic(error: unknown): string {
  const message = error instanceof Error ? error.message : String(error);
  return message
    .replace(/https?:\/\/\S+/gi, '[resource URL]')
    .replace(/([?&]key=)[^&\s]+/gi, '$1[redacted]');
}

export default function VancouverMap() {
  const containerRef = useRef<HTMLDivElement>(null);
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
      if (import.meta.env.DEV) {
        console.error('RouteLens could not initialize MapLibre.', safeDiagnostic(error));
      }
      return;
    }

    const attribution = new AttributionControl({ compact: false });
    map.addControl(attribution, 'bottom-right');
    map.addControl(new NavigationControl({ showCompass: true }), 'top-right');

    let sawResourceError = false;
    let failureTimer: ReturnType<typeof setTimeout> | undefined;
    const handleLoad = () => {
      if (failureTimer) {
        clearTimeout(failureTimer);
        failureTimer = undefined;
      }
      setStatus('ready');
    };
    const handleError = (event: ErrorEvent) => {
      // MapLibre reports both tile and style failures through one event. Give
      // the initial load time to recover before showing a fatal map state.
      sawResourceError = true;
      if (!failureTimer) {
        failureTimer = setTimeout(() => {
          if (map.loaded()) return;
          setStatus('error');
          if (import.meta.env.DEV && sawResourceError) {
            console.error(
              'RouteLens map resources failed to load. Check MapTiler connectivity and MAPTILER_API_KEY.',
              safeDiagnostic(event.error),
            );
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
    };
  }, [apiKey]);

  return (
    <section className="map-frame" aria-label="Interactive map of Vancouver">
      <div className="map-canvas" ref={containerRef} />
      {!apiKey ? (
        <div className="map-message" role="status">
          <h2>Map configuration required</h2>
          <p>
            Add <code>MAPTILER_API_KEY</code> to the project root <code>.env</code>, then restart
            the Vite server.
          </p>
        </div>
      ) : status === 'loading' ? (
        <div className="map-message map-message-loading" role="status" aria-live="polite">
          <span className="map-spinner" aria-hidden="true" />
          <span>Loading Vancouver map…</span>
        </div>
      ) : status === 'error' ? (
        <div className="map-message" role="alert">
          <h2>Map unavailable</h2>
          <p>MapTiler could not load the Vancouver basemap. Check the connection and map key.</p>
          {import.meta.env.DEV && (
            <p className="map-diagnostic">Development hint: verify MAPTILER_API_KEY in the root .env.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}
