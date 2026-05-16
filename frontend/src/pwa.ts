/// <reference types="vite-plugin-pwa/client" />
import { registerSW } from 'virtual:pwa-register';

if (typeof window !== 'undefined') {
  const updateSW = registerSW({
    onNeedRefresh() {
      if (confirm('New content available. Reload?')) {
        updateSW(true);
      }
    },
    onOfflineReady() {
      console.log('App ready to work offline');
    },
  });
}
