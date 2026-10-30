export type JourneyPresentation = { stage: 'plan'; analysisAt: null } | { stage: 'understand'; analysisAt: string };

export const initialJourneyPresentation: JourneyPresentation = { stage: 'plan', analysisAt: null };

export function beginJourneyPresentation(
  current: JourneyPresentation,
  validAnalysis: boolean,
  analysisAt: string,
): JourneyPresentation {
  return validAnalysis ? { stage: 'understand', analysisAt } : current;
}

export function invalidateJourneyPresentation(): JourneyPresentation {
  return initialJourneyPresentation;
}
