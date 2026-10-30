import DestinationCameraPanel from './DestinationCameraPanel';
import DestinationWeatherPanel from './DestinationWeatherPanel';
import type { AnalysisState } from './analysisTypes';
import type { CameraState } from './cameras';
import { roadAheadSummary } from './journeySummary';

export default function JourneyPrimarySummary({ analysis, camera, analysisAt }: {
  analysis: AnalysisState;
  camera: CameraState;
  analysisAt: string;
}) {
  const roadAhead = roadAheadSummary(analysis);
  return <section className="journey-primary-summary" id="understand-your-journey" aria-labelledby="understand-journey-title">
    <header className="primary-summary-heading">
      <div><p className="eyebrow">JOURNEY EVIDENCE</p><h2 id="understand-journey-title">Understand Your Journey</h2></div>
      <p>Destination conditions and route evidence load independently.</p>
    </header>
    <div className="primary-summary-columns">
      <div className="primary-summary-camera"><DestinationCameraPanel camera={camera} headingId="primary-destination-camera-title" /></div>
      <div className="primary-summary-weather"><DestinationWeatherPanel analysis={analysis} presentation="primary" analysisAt={analysisAt} headingId="primary-destination-weather-title" /></div>
    </div>
    <div className={`road-ahead-summary road-ahead-summary-${roadAhead.status}`} role={roadAhead.status === 'unavailable' ? 'status' : undefined}>
      <span className="eyebrow">ROAD AHEAD · ROUTE OVERLAPS</span>
      <p>{roadAhead.message}</p>
    </div>
  </section>;
}
