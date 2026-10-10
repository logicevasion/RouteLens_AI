import { useEffect, useState } from 'react';

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
    <main className="min-h-screen bg-[#090d12] px-6 py-10 text-slate-100 sm:px-10">
      <div className="mx-auto flex min-h-[calc(100vh-5rem)] max-w-5xl flex-col">
        <header className="flex items-center justify-between border-b border-white/10 pb-5">
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

        <section className="flex flex-1 flex-col justify-center py-20">
          <p className="mb-5 text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">
            Application foundation
          </p>
          <h1 className="max-w-2xl text-4xl font-semibold leading-tight tracking-tight text-white sm:text-6xl">
            A clearer picture of the city is taking shape.
          </h1>
          <p className="mt-6 max-w-xl text-base leading-7 text-slate-400">
            RouteLens AI brings public city information into one place. The application shell is
            running; journey tools and the interactive map are not part of this foundation yet.
          </p>
          <div className="mt-10 flex items-center gap-3 text-sm text-slate-500">
            <span className="h-px w-10 bg-cyan-300/60" />
            Local development environment
          </div>
        </section>

        <footer className="border-t border-white/10 pt-4 text-xs text-slate-600">
          RouteLens AI · Vancouver
        </footer>
      </div>
    </main>
  );
}
