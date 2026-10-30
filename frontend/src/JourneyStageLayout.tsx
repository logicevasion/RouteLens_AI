import type { ReactNode } from 'react';
import JourneyPrimarySummary from './JourneyPrimarySummary';
import type { AnalysisState } from './analysisTypes';
import type { CameraState } from './cameras';

export default function JourneyStageLayout({ stage, analysis, camera, analysisAt, children }: {
  stage: 'plan' | 'understand';
  analysis: AnalysisState;
  camera: CameraState;
  analysisAt: string;
  children: ReactNode;
}) {
  return <>
    {stage === 'understand' && <div className="summary-anchor">
      <JourneyPrimarySummary analysis={analysis} camera={camera} analysisAt={analysisAt} />
    </div>}
    {children}
  </>;
}
