import "./styles/tokens.css";
import "./styles/base.css";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

createRoot(document.getElementById("root")!).render(<App />);

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(err => {
      console.error('SW registration failed:', err);
    });
  });
}

try {
  const tg = (window as any)?.Telegram?.WebApp;
  if (tg && typeof tg.ready === 'function') {
    tg.ready();
  }
} catch {
}
