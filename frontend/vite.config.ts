import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig(({ mode }) => {
  const rootEnv = loadEnv(mode, '..', '');

  return {
    plugins: [react(), tailwindcss()],
    // Explicitly define only the browser-usable MapTiler key. Other root .env
    // values remain available to Vite's config process only.
    envPrefix: [],
    define: {
      'import.meta.env.VITE_MAPTILER_API_KEY': JSON.stringify(
        rootEnv.MAPTILER_API_KEY ?? '',
      ),
    },
    server: {
      proxy: {
        '/api': 'http://localhost:8000',
      },
    },
  };
});
