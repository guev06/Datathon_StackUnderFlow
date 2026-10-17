import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  // In dev, API calls go to the FlowState backend (uvicorn on :8000).
  server: { proxy: { '/api': 'http://localhost:8000' } },
});
