import { useEffect, useState } from 'react';
import VancouverMap from './VancouverMap';

type BackendStatus = 'checking' | 'connected' | 'unavailable';

const statusLabels: Record<BackendStatus, string> = {
  checking: 'Checking backend…',
  connected: 'Backend connected',
  unavailable: 'Backend unavailable',
};

export default function App() {
  const [backendStatus, setBackendStatus] = useState<BackendStatus>('checking');

  useEffect(() => {
    const controller = new AbortController();

    async function checkBackend() {
      try {
        const response = await fetch('/api/health', { signal: controller.signal });
        if (!response.ok) {
          throw new Error(`Health request returned ${response.status}`);
        }

        const body: unknown = await response.json();
        const isHealthy =
          typeof body === 'object' &&
          body !== null &&
          'status' in body &&
          body.status === 'ok';

        setBackendStatus(isHealthy ? 'connected' : 'unavailable');
      } catch {
        if (!controller.signal.aborted) {
          setBackendStatus('unavailable');
        }
      }
    }

    void checkBackend();
    return () => controller.abort();
  }, []);

  return (
    <main className="min-h-screen bg-[#090d12] px-4 py-6 text-slate-100 sm:px-8">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-[1440px] flex-col">
        <header className="flex items-center justify-between border-b border-white/10 pb-4">
          <a className="text-lg font-semibold tracking-tight text-white" href="/">
            RouteLens <span className="text-cyan-300">AI</span>
          </a>
          <div
            className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-slate-300"
            role="status"
            aria-live="polite"
          >
            <span
              className={`h-2 w-2 rounded-full ${
                backendStatus === 'connected'
                  ? 'bg-emerald-400'
                  : backendStatus === 'unavailable'
                    ? 'bg-rose-400'
                    : 'animate-pulse bg-amber-300'
              }`}
              aria-hidden="true"
            />
            {statusLabels[backendStatus]}
          </div>
        </header>

        <section className="flex flex-col gap-5 py-6">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">
              Vancouver · British Columbia
            </p>
            <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">
              See the city around your journey.
            </h1>
          </div>
          <VancouverMap />
          <p className="text-sm text-slate-500">
            Explore Vancouver on the map. Journey tools are coming in a later phase.
          </p>
        </section>

        <footer className="border-t border-white/10 pt-4 text-xs text-slate-600">
          RouteLens AI · Vancouver
        </footer>
      </div>
    </main>
  );
}
