import type { AnalysisState, AnalysisFinding, SourceStatus } from './analysisTypes';
import { eventDescription, eventTitle, eventTypeLabel, formatAge, hasUsableGeometry, officialDetailLinkLabel, officialDetailUrl } from './roadAhead';

type RoadAheadPanelProps = {
  analysis: AnalysisState;
  selectedEventId: string | null;
  onSelectFinding: (eventId: string) => void;
};

function sourceName(status: SourceStatus): string {
  return status.dataset_id === 'road-ahead-current-road-closures' ? 'Current road closures'
    : status.dataset_id === 'road-ahead-projects-under-construction' ? 'Projects under construction'
      : 'Road Ahead dataset';
}

function freshness(status: SourceStatus): string {
  if (!status.available) return 'Unavailable';
  if (status.stale) return `Stale cached data${formatAge(status.cache_age_seconds) ? ` · ${formatAge(status.cache_age_seconds)}` : ''}`;
  if (status.cache_hit) return `Cached data${formatAge(status.cache_age_seconds) ? ` · ${formatAge(status.cache_age_seconds)}` : ''}`;
  if (status.refreshed) return 'Retrieved from source';
  return 'Available';
}

function EventFinding({ finding, selected, onSelect }: { finding: AnalysisFinding; selected: boolean; onSelect: () => void }) {
  const title = eventTitle(finding);
  const description = eventDescription(finding);
  const location = finding.detail.location ?? null;
  const status = finding.detail.status ?? finding.event.status;
  const schedule = finding.detail.schedule_text ?? finding.event.schedule_text;
  const restriction = finding.detail.restriction_text ?? finding.event.restriction_text;
  const sourceLink = officialDetailUrl(finding.detail.source_url ?? finding.event.source_url);
  const detailUnavailable = finding.detail.availability === 'unavailable' || finding.detail.availability === 'parse_failed';
  const noSupportedDetail = finding.detail.availability === 'no_supported_fields';
  const hasMapGeometry = hasUsableGeometry(finding.event.geometry);

  return (
    <article className={`road-finding${selected ? ' road-finding-selected' : ''}`}>
      <button className="finding-select" type="button" aria-pressed={selected} onClick={onSelect}>
        <span className={`finding-kind finding-kind-${finding.classification}`}>
          {finding.classification === 'direct_overlap' ? 'On your route' : 'Nearby'}
        </span>
        <span className="finding-distance">{eventTypeLabel(finding)}</span>
        <span className="finding-title">{title}</span>
        {finding.classification === 'nearby' && <span className="finding-distance">{Math.round(finding.distance_meters)} m away</span>}
        <span className="finding-map-hint">{hasMapGeometry ? selected ? 'Highlighted on map' : 'Show on map' : 'Map location unavailable'}</span>
      </button>
      {(location || status || schedule || restriction || description || sourceLink || detailUnavailable || noSupportedDetail || finding.detail.from_cache || finding.detail.stale) && (
        <details className="finding-details">
          <summary>Event details</summary>
          <div className="finding-detail-copy">
            {location && <p><strong>Location</strong>{location}</p>}
            {status && <p><strong>Source status</strong>{status}</p>}
            {schedule && <p><strong>Expected schedule</strong>{schedule}</p>}
            {restriction && <p><strong>Source restriction</strong>{restriction}</p>}
            {description && <p><strong>Description</strong>{description}</p>}
            {detailUnavailable && <p className="finding-detail-note">Additional detail is unavailable; the dataset event is still shown.</p>}
            {noSupportedDetail && <p className="finding-detail-note">No additional labeled detail was available; the dataset event is still shown.</p>}
            {finding.detail.from_cache && !finding.detail.stale && <p className="finding-detail-note">Additional detail came from the local cache{finding.detail.retrieved_at ? ` · retrieved ${new Date(finding.detail.retrieved_at).toLocaleString()}` : ''}.</p>}
            {finding.detail.stale && <p className="finding-detail-note">Showing previously cached detail{finding.detail.retrieved_at ? ` retrieved ${new Date(finding.detail.retrieved_at).toLocaleString()}` : ''}.</p>}
            {sourceLink && <a href={sourceLink} target="_blank" rel="noopener noreferrer">{officialDetailLinkLabel(finding.detail.availability)}</a>}
          </div>
        </details>
      )}
    </article>
  );
}

export default function RoadAheadPanel({ analysis, selectedEventId, onSelectFinding }: RoadAheadPanelProps) {
  const result = analysis.status === 'success' ? analysis.result : null;
  const direct = result?.findings.filter((finding) => finding.classification === 'direct_overlap') ?? [];
  const nearby = result?.findings.filter((finding) => finding.classification === 'nearby') ?? [];

  return (
    <section className="road-ahead-panel" aria-labelledby="road-ahead-title">
      <div className="road-ahead-heading">
        <div>
          <p className="eyebrow">ROAD AHEAD</p>
          <h3 id="road-ahead-title">Along your route</h3>
        </div>
        {result && <span className={`analysis-badge analysis-${result.status}`}>{result.status === 'available' ? 'Available' : result.status === 'partial' ? 'Partial' : 'Unavailable'}</span>}
      </div>

      {analysis.status === 'idle' && <p className="road-ahead-state">Select a driving route, then analyze to check available City of Vancouver Road Ahead data.</p>}
      {analysis.status === 'loading' && (
        <p className="road-ahead-state road-ahead-loading" role="status" aria-live="polite"><span className="map-spinner" aria-hidden="true" /> Checking Road Ahead datasets and matching route events…</p>
      )}
      {analysis.status === 'error' && <p className="road-ahead-state road-ahead-error" role="alert">{analysis.error}</p>}

      {result && <>
        <p className="analysis-summary">{result.summary}</p>
        {result.status === 'partial' && <p className="coverage-note">Coverage is incomplete because one or more Road Ahead datasets could not be checked.</p>}
        {result.status === 'unavailable' && <p className="coverage-note">No event coverage was available. This does not indicate a clear route.</p>}
        <div className="source-status-list" aria-label="Road Ahead source status">
          {result.source_statuses.map((status) => (
            <div className={`source-status source-${status.available ? status.stale ? 'stale' : 'available' : 'unavailable'}`} key={status.dataset_id}>
              <span className="source-status-name">{sourceName(status)}</span>
              <span>{freshness(status)}</span>
              {status.fetched_at && <time dateTime={status.fetched_at}>Checked {new Date(status.fetched_at).toLocaleString()}</time>}
              {status.error && <span className="source-error">Source could not be retrieved.</span>}
            </div>
          ))}
        </div>

        {direct.length > 0 && <FindingGroup title="Route intersections" findings={direct} selectedEventId={selectedEventId} onSelectFinding={onSelectFinding} />}
        {nearby.length > 0 && <FindingGroup title="Nearby context" findings={nearby} selectedEventId={selectedEventId} onSelectFinding={onSelectFinding} />}
        {result.status !== 'unavailable' && result.findings.length === 0 && (
          <p className="road-ahead-empty">No relevant Road Ahead events were identified in the available datasets. This does not confirm that the route is disruption-free.</p>
        )}
        {result.unmatchable_events.length > 0 && <p className="coverage-note">{result.unmatchable_events.length} source {result.unmatchable_events.length === 1 ? 'event had' : 'events had'} geometry that could not be checked.</p>}
        <p className="analysis-timestamp">Analysis requested {new Date(result.analyzed_at).toLocaleString()} · City of Vancouver Open Data</p>
      </>}
    </section>
  );
}

function FindingGroup({ title, findings, selectedEventId, onSelectFinding }: {
  title: string;
  findings: AnalysisFinding[];
  selectedEventId: string | null;
  onSelectFinding: (eventId: string) => void;
}) {
  return (
    <section className="finding-group" aria-label={title}>
      <h4>{title} <span>{findings.length}</span></h4>
      {findings.map((finding) => (
        <EventFinding key={finding.event.id} finding={finding} selected={selectedEventId === finding.event.id} onSelect={() => onSelectFinding(finding.event.id)} />
      ))}
    </section>
  );
}
