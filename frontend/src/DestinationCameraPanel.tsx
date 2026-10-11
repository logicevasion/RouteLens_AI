import { useEffect, useRef, useState } from 'react';
import type { CameraState, CameraView } from './cameras';
import { formatCameraAge, formatRetrievedAt, handleCameraImageError } from './cameras';

function cameraDistance(metres: number): string {
  return metres >= 1000 ? `${(metres / 1000).toFixed(1)} km` : `${Math.round(metres)} m`;
}

function CameraImage({ view, intersection, requestKey, stale }: { view: CameraView; intersection: string; requestKey: string; stale: boolean }) {
  const [failed, setFailed] = useState(false);
  const activeRequestKey = useRef(requestKey);
  activeRequestKey.current = requestKey;

  useEffect(() => setFailed(false), [requestKey, view.image_reference]);

  if (failed) return <div className="camera-image-failed" role="status">This camera image could not be loaded.</div>;
  const direction = view.direction_label?.trim() || 'Direction not provided';
  return <figure className={`camera-view${stale || view.stale ? ' camera-view-stale' : ''}`}>
    <div className="camera-image-frame" style={{ aspectRatio: `${view.width} / ${view.height}` }}>
      <img
        src={view.image_reference}
        alt={`${intersection} — ${direction} camera view`}
        loading="lazy"
        onError={() => {
          handleCameraImageError(requestKey, activeRequestKey.current, () => setFailed(true));
        }}
      />
    </div>
    <figcaption>
      <strong>{direction}</strong>
      {stale || view.stale ? <span>Cached image — may be outdated</span> : null}
      <small>Camera image retrieved at {formatRetrievedAt(view.retrieved_at)} · Retrieved {formatCameraAge(view.cache_age_seconds)}</small>
      {view.source_capture_at && <small>Source capture time {formatRetrievedAt(view.source_capture_at)}</small>}
      {!view.source_capture_at && <small>Camera capture time unavailable</small>}
    </figcaption>
  </figure>;
}

export default function DestinationCameraPanel({ camera }: { camera: CameraState }) {
  const result = camera.status === 'success' ? camera.result : null;
  const intersection = result?.intersection;
  const views = result?.status === 'stale' ? result.stale_views : [...(result?.views ?? []), ...(result?.stale_views ?? [])];
  const partial = Boolean(result && (result.diagnostics.views_failed > 0 || result.stale_views.length > 0));
  return <section className="destination-camera-panel" aria-labelledby="destination-camera-title">
    <div className="camera-heading">
      <div><p className="eyebrow">NEARBY INTERSECTION</p><h3 id="destination-camera-title">Destination Cameras</h3></div>
      {result && <span className={`camera-badge${result.status === 'unavailable' ? ' camera-badge-muted' : ''}`}>{result.status === 'available' ? 'Camera images' : result.status === 'stale' ? 'Stale images' : 'Unavailable'}</span>}
    </div>
    {camera.status === 'idle' && <p className="camera-state">Camera images load when you choose Analyze journey.</p>}
    {camera.status === 'loading' && <p className="camera-state" role="status"><span className="map-spinner" aria-hidden="true" /> Finding nearby camera views…</p>}
    {camera.status === 'error' && <p className="camera-state camera-error" role="status">Camera images are temporarily unavailable. Road and weather results are unaffected.</p>}
    {result?.status === 'unavailable' && <p className="camera-state" role="status">No usable camera images were found within the available search area.</p>}
    {intersection && <>
      <div className="camera-intersection">
        <strong>{intersection.name}</strong>
        <span>Approximately {cameraDistance(intersection.distance_metres)} from destination</span>
        <p>Images are from a nearby intersection and may not show the destination itself.</p>
        <a href={intersection.official_page_url} target="_blank" rel="noopener noreferrer">Official City of Vancouver camera page</a>
      </div>
      {result?.status === 'stale' && <p className="camera-stale-note" role="status">Only cached camera images are available. They may be outdated and do not establish current conditions.</p>}
      {result?.diagnostics.catalogue_stale && <p className="camera-stale-note">Camera catalogue information is stale.</p>}
      {partial && result?.status !== 'stale' && <p className="camera-stale-note" role="status">Some directions were unavailable or stale during the nearby camera search. Available views below are from this selected intersection.</p>}
      <div className="camera-gallery" aria-label={`Camera views at ${intersection.name}`}>
        {views.map((view) => <CameraImage
          key={`${camera.status === 'success' ? camera.requestKey : ''}:${view.view_id}`}
          view={view}
          intersection={intersection.name}
          requestKey={camera.status === 'success' ? camera.requestKey : ''}
          stale={result?.status === 'stale'}
        />)}
      </div>
      <p className="camera-attribution">Source: {intersection.source} · {intersection.attribution}</p>
    </>}
  </section>;
}
