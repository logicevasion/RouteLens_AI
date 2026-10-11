import type { AnalysisState, AnalysisFinding, DriveBCAnalysisFinding, SourceStatus } from './analysisTypes';
import { eventDescription, eventTitle, eventTypeLabel, formatAge, hasUsableGeometry, officialDetailLinkLabel, officialDetailUrl, sourceScopedEventId } from './roadAhead';
import { driveBCRelationLabel, officialDriveBCUrl } from './drivebc';

type RoadAheadPanelProps = {
  analysis: AnalysisState;
  selectedEventId: string | null;
  onSelectFinding: (eventId: string) => void;
};

function sourceName(status: SourceStatus): string {
  return status.dataset_id === 'road-ahead-current-road-closures' ? 'Road Ahead · Current road closures'
    : status.dataset_id === 'road-ahead-projects-under-construction' ? 'Road Ahead · Projects under construction'
      : status.dataset_id.startsWith('drivebc-open511') ? 'DriveBC · Open511 regional events'
        : status.source;
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
        <span className={`finding-kind finding-kind-${finding.classification}`}>{finding.classification === 'direct_overlap' ? 'On your route' : 'Nearby'}</span>
        <span className="finding-distance">{eventTypeLabel(finding)}</span>
        <span className="finding-title">{title}</span>
        {finding.classification === 'nearby' && <span className="finding-distance">{Math.round(finding.distance_meters)} m away</span>}
        <span className="finding-map-hint">{hasMapGeometry ? selected ? 'Highlighted on map' : 'Show on map' : 'Map location unavailable'}</span>
      </button>
      {(location || status || schedule || restriction || description || sourceLink || detailUnavailable || noSupportedDetail || finding.detail.from_cache || finding.detail.stale) && (
        <details className="finding-details"><summary>Event details</summary><div className="finding-detail-copy">
          {location && <p><strong>Location</strong>{location}</p>}{status && <p><strong>Source status</strong>{status}</p>}
          {schedule && <p><strong>Expected schedule</strong>{schedule}</p>}{restriction && <p><strong>Source restriction</strong>{restriction}</p>}
          {description && <p><strong>Description</strong>{description}</p>}
          {detailUnavailable && <p className="finding-detail-note">Additional detail is unavailable; the dataset event is still shown.</p>}
          {noSupportedDetail && <p className="finding-detail-note">No additional labeled detail was available; the dataset event is still shown.</p>}
          {finding.detail.from_cache && !finding.detail.stale && <p className="finding-detail-note">Additional detail came from the local cache{finding.detail.retrieved_at ? ` · retrieved ${new Date(finding.detail.retrieved_at).toLocaleString()}` : ''}.</p>}
          {finding.detail.stale && <p className="finding-detail-note">Showing previously cached detail{finding.detail.retrieved_at ? ` retrieved ${new Date(finding.detail.retrieved_at).toLocaleString()}` : ''}.</p>}
          {sourceLink && <a href={sourceLink} target="_blank" rel="noopener noreferrer">{officialDetailLinkLabel(finding.detail.availability)}</a>}
        </div></details>
      )}
    </article>
  );
}

function DriveBCFinding({ finding, selected, onSelect }: { finding: DriveBCAnalysisFinding; selected: boolean; onSelect: () => void }) {
  const event = finding.event;
  const evidence = finding.source_evidence;
  const basis = finding.geometry_basis;
  const relation = driveBCRelationLabel(basis);
  const link = officialDriveBCUrl(event.source_url);
  const roadEvidence = evidence.roads.flatMap((road) => {
    const name = typeof road.name === 'string' ? road.name : typeof road.road_name === 'string' ? road.road_name : null;
    const direction = typeof road.direction === 'string' ? road.direction : null;
    return name || direction ? [`${name ?? 'Road'}${direction ? ` · ${direction}` : ''}`] : [];
  });
  return <article className={`road-finding drivebc-finding${selected ? ' road-finding-selected' : ''}`}>
    <button className="finding-select" type="button" aria-pressed={selected} onClick={onSelect}>
      <span className={`finding-kind finding-kind-${finding.classification}`}>{relation}</span>
      <span className="finding-distance">{evidence.severity ?? 'Severity unreported'}</span>
      <span className="finding-title">{event.title}</span>
      <span className="finding-distance">{evidence.event_type.replaceAll('_', ' ')}</span>
      {finding.classification === 'nearby' && <span className="finding-distance">{Math.round(finding.distance_meters)} m away</span>}
      <span className="finding-map-hint">{selected ? 'Highlighted on map' : 'Show on map'} · DriveBC regional event</span>
    </button>
    <div className="finding-details drivebc-details"><div className="finding-detail-copy">
      <p><strong>Source</strong>{event.source}</p>
      {roadEvidence.length > 0 && <p><strong>Road and reported direction</strong>{roadEvidence.join('; ')}</p>}
      {evidence.status && <p><strong>Source record status</strong>{evidence.status}</p>}
      {evidence.schedule_text && <p><strong>Source schedule</strong>{evidence.schedule_text}</p>}
      {event.updated_at && <p><strong>Provider update</strong>{new Date(event.updated_at).toLocaleString()}</p>}
      <p className="finding-detail-note">{evidence.direction_assessment === 'undetermined' ? 'Direction not verified.' : `Direction assessment: ${evidence.direction_assessment}.`} {evidence.temporal_applicability === 'unknown' ? 'Schedule applicability is unknown.' : `Temporal applicability: ${evidence.temporal_applicability}.`} {evidence.current_impact === 'not_established' ? 'Current impact not established.' : `Current impact assessment: ${evidence.current_impact}.`} An ACTIVE source status does not confirm an effect on traffic right now.</p>
      {link && <a href={link} target="_blank" rel="noopener noreferrer">Open official DriveBC event ↗</a>}
      <p className="provider-attribution">{event.attribution}</p>
    </div></div>
  </article>;
}

export default function RoadAheadPanel({ analysis, selectedEventId, onSelectFinding }: RoadAheadPanelProps) {
  const result = analysis.status === 'success' ? analysis.result : null;
  const direct = result?.findings.filter((finding) => finding.classification === 'direct_overlap') ?? [];
  const nearby = result?.findings.filter((finding) => finding.classification === 'nearby') ?? [];
  const drivebc = result?.drivebc_findings ?? [];
  const driveDirect = drivebc.filter((finding) => finding.geometry_basis === 'linestring_intersection');
  const driveNearby = drivebc.filter((finding) => finding.geometry_basis !== 'linestring_intersection');
  const selectedRegional = result?.regional_events.find((event) => sourceScopedEventId(event) === selectedEventId) ?? null;
  const roadAheadUsable = result?.source_statuses.some((status) => status.dataset_id.startsWith('road-ahead-') && status.available) ?? false;
  const driveBCUsable = result?.source_statuses.some((status) => status.dataset_id.startsWith('drivebc-open511') && status.available) ?? false;

  return <section className="road-ahead-panel multi-source-panel" aria-labelledby="road-context-title">
    <div className="road-ahead-heading"><div><p className="eyebrow">MULTI-SOURCE ROAD CONTEXT</p><h3 id="road-context-title">Along your journey</h3></div>
      {result && <span className={`analysis-badge analysis-${result.status}`}>{result.status === 'available' ? 'Available' : result.status === 'partial' ? 'Partial' : 'Unavailable'}</span>}
    </div>
    {analysis.status === 'idle' && <p className="road-ahead-state">Select a driving route, then analyze to check Road Ahead and DriveBC data.</p>}
    {analysis.status === 'loading' && <p className="road-ahead-state road-ahead-loading" role="status" aria-live="polite"><span className="map-spinner" aria-hidden="true" /> Checking road datasets and matching route events…</p>}
    {analysis.status === 'error' && <p className="road-ahead-state road-ahead-error" role="alert">{analysis.error}</p>}
    {result && <>
      <p className="analysis-summary">{result.summary}</p>
      {result.status === 'unavailable' && <p className="coverage-note">No source coverage was available. This does not indicate a clear route.</p>}
      <div className="source-status-list" aria-label="Road event source status">{result.source_statuses.map((status) =>
        <div className={`source-status source-${status.available ? status.stale ? 'stale' : 'available' : 'unavailable'}`} key={status.dataset_id}>
          <span className="source-status-name">{sourceName(status)}</span><span>{freshness(status)}</span>
          {status.available && <span className="source-record-count">{status.records_received} source records</span>}
          {status.fetched_at && <time dateTime={status.fetched_at}>Checked {new Date(status.fetched_at).toLocaleString()}</time>}
          {!status.available && <span className="source-error">Coverage from this dataset is reduced.</span>}
        </div>)}</div>
      <section className="source-finding-section" aria-label="Road Ahead findings"><h4>Road Ahead · City of Vancouver</h4>
        {direct.length > 0 && <FindingGroup title="Route intersections" findings={direct} selectedEventId={selectedEventId} onSelectFinding={onSelectFinding} />}
        {nearby.length > 0 && <FindingGroup title="Nearby context" findings={nearby} selectedEventId={selectedEventId} onSelectFinding={onSelectFinding} />}
        {result.findings.length === 0 && (roadAheadUsable
          ? <p className="road-ahead-empty">No route-relevant findings were identified in available Road Ahead datasets. This does not confirm that the route is disruption-free.</p>
          : <p className="road-ahead-empty">Road Ahead route findings could not be checked because its datasets are unavailable.</p>)}
      </section>
      <section className="source-finding-section" aria-label="DriveBC findings"><h4>DriveBC Open511 · route-relevant findings</h4>
        {driveDirect.length > 0 && <DriveBCGroup title="LineString intersections" findings={driveDirect} selectedEventId={selectedEventId} onSelectFinding={onSelectFinding} />}
        {driveNearby.length > 0 && <DriveBCGroup title="Nearby events" findings={driveNearby} selectedEventId={selectedEventId} onSelectFinding={onSelectFinding} />}
        {drivebc.length === 0 && (driveBCUsable
          ? <p className="road-ahead-empty">No route-relevant DriveBC findings were identified. Regional events may still appear on the map; this is not proof the route is clear.</p>
          : <p className="road-ahead-empty">DriveBC route findings could not be checked because the Open511 source is unavailable.</p>)}
      </section>
      {selectedRegional && <div className="regional-selection" aria-live="polite"><strong>Selected regional event · {selectedRegional.source}</strong><span>{selectedRegional.title}</span><small>This event is visible in the regional feed; selection alone does not make it route-relevant.</small></div>}
      {result.unmatchable_events.length > 0 && <p className="coverage-note">{result.unmatchable_events.length} source events had geometry that could not be checked.</p>}
      <p className="analysis-timestamp">Analysis requested {new Date(result.analyzed_at).toLocaleString()} · regional DriveBC events shown on map are separate from route findings</p>
    </>}
  </section>;
}

function FindingGroup({ title, findings, selectedEventId, onSelectFinding }: { title: string; findings: AnalysisFinding[]; selectedEventId: string | null; onSelectFinding: (eventId: string) => void }) {
  return <section className="finding-group" aria-label={title}><h5>{title} <span>{findings.length}</span></h5>{findings.map((finding) => {
    const id = sourceScopedEventId(finding.event);
    return <EventFinding key={id} finding={finding} selected={selectedEventId === id} onSelect={() => onSelectFinding(id)} />;
  })}</section>;
}

function DriveBCGroup({ title, findings, selectedEventId, onSelectFinding }: { title: string; findings: DriveBCAnalysisFinding[]; selectedEventId: string | null; onSelectFinding: (eventId: string) => void }) {
  return <section className="finding-group" aria-label={title}><h5>{title} <span>{findings.length}</span></h5>{findings.map((finding) => {
    const id = sourceScopedEventId(finding.event);
    return <DriveBCFinding key={id} finding={finding} selected={selectedEventId === id} onSelect={() => onSelectFinding(id)} />;
  })}</section>;
}
