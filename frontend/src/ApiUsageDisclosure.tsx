import { useEffect, useRef, useState } from 'react';
import type { KeyboardEvent, ToggleEvent } from 'react';

const providerLabels: Record<string, string> = {
  maptiler: 'MapTiler geocoding',
  openrouteservice: 'openrouteservice',
  openweather: 'OpenWeather',
  eccc_swob: 'ECCC / SWOB',
  drivebc_open511: 'DriveBC Open511',
  vancouver_road_ahead: 'Vancouver Road Ahead',
  vancouver_traffic_cameras: 'Vancouver camera images',
  openrouter: 'OpenRouter',
  maptiler_map_resources: 'MapTiler map resources',
};

type ProviderUsage = {
  provider: string;
  status: 'tracked' | 'untracked' | 'unavailable';
  attempts: number | null;
};

type UsageReport = {
  start_date: string;
  end_date: string;
  status: 'ok' | 'degraded' | 'unavailable';
  providers: ProviderUsage[];
};

type UsageState = { kind: 'loading' | 'error' } | { kind: 'ready'; report: UsageReport };

function parseReport(value: unknown): UsageReport {
  const report = value as Partial<UsageReport> | null;
  if (
    !report || typeof report.start_date !== 'string' || typeof report.end_date !== 'string' ||
    !['ok', 'degraded', 'unavailable'].includes(report.status ?? '') ||
    !Array.isArray(report.providers) || !report.providers.every((row) =>
      row && typeof row.provider === 'string' && Object.hasOwn(providerLabels, row.provider) &&
      (row.status === 'tracked'
        ? typeof row.attempts === 'number' && Number.isInteger(row.attempts) && row.attempts >= 0
        : ['untracked', 'unavailable'].includes(row.status) && row.attempts === null),
    )
  ) {
    throw new Error('Invalid usage response');
  }
  return report as UsageReport;
}

export default function ApiUsageDisclosure() {
  const [state, setState] = useState<UsageState>({ kind: 'loading' });
  const request = useRef<AbortController | null>(null);

  useEffect(() => () => request.current?.abort(), []);

  async function toggle(event: ToggleEvent<HTMLDetailsElement>) {
    request.current?.abort();
    setState({ kind: 'loading' });
    if (!event.currentTarget.open) return;

    const controller = new AbortController();
    request.current = controller;
    try {
      const response = await fetch('/api/usage', { signal: controller.signal });
      if (!response.ok) throw new Error('Usage request failed');
      const report = parseReport(await response.json());
      if (!controller.signal.aborted) setState({ kind: 'ready', report });
    } catch {
      if (!controller.signal.aborted) setState({ kind: 'error' });
    }
  }

  function closeOnEscape(event: KeyboardEvent<HTMLDetailsElement>) {
    if (event.key === 'Escape' && event.currentTarget.open) {
      event.currentTarget.open = false;
      event.currentTarget.querySelector('summary')?.focus();
    }
  }

  const report = state.kind === 'ready' ? state.report : null;
  return (
    <details className="api-usage" onToggle={(event) => void toggle(event)} onKeyDown={closeOnEscape}>
      <summary>API Usage</summary>
      <section className="api-usage-panel" aria-label="API usage report">
        <h2>API Usage — Last 30 Days</h2>
        <p>Backend-observed outbound attempts. Camera counts cover image requests only. Provider-account totals may differ.</p>
        <div aria-live="polite">
          {state.kind === 'loading' && <p>Loading usage…</p>}
          {state.kind === 'error' && <p>Could not load API usage. Reopen to try again.</p>}
          {report && (
            <>
              <p>{report.start_date} – {report.end_date} (UTC)</p>
              {report.status === 'degraded' && <p>Tracking is degraded. Counts may be incomplete.</p>}
              {report.status === 'unavailable' && <p>Usage tracking is currently unavailable.</p>}
              <dl>
                {report.providers.filter((row) => row.status !== 'unavailable').map((row) => (
                  <div key={row.provider}>
                    <dt>{providerLabels[row.provider]}</dt>
                    <dd>{row.status === 'untracked' ? 'Untracked' : row.attempts?.toLocaleString()}</dd>
                  </div>
                ))}
              </dl>
            </>
          )}
        </div>
      </section>
    </details>
  );
}
