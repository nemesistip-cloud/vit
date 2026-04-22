import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

const htmlBypass = (req: any) => {
  if (req.headers.accept?.includes("text/html")) return "/index.html";
  return null;
};

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "src"),
      "@workspace/api-client-react/src/generated/api.schemas": path.resolve(__dirname, "src/api-client/schemas.ts"),
      "@workspace/api-client-react": path.resolve(__dirname, "src/api-client/index.ts"),
    },
    dedupe: ["react", "react-dom"],
  },
  build: {
    outDir: path.resolve(__dirname, "dist"),
    emptyOutDir: true,
  },
  server: {
    port: 5000,
    host: "0.0.0.0",
    allowedHosts: true,
    proxy: {
      "/auth": { target: "http://localhost:8000", bypass: htmlBypass },
      "/api": { target: "http://localhost:8000", ws: true },
      "/matches": { target: "http://localhost:8000", bypass: htmlBypass },
      "/predict": { target: "http://localhost:8000", bypass: htmlBypass },
      "/history": { target: "http://localhost:8000", bypass: htmlBypass },
      "/result": { target: "http://localhost:8000", bypass: htmlBypass },
      "/results": { target: "http://localhost:8000", bypass: htmlBypass },
      "/analytics": { target: "http://localhost:8000", bypass: htmlBypass },
      "/admin": { target: "http://localhost:8000", bypass: htmlBypass },
      "/health": { target: "http://localhost:8000", bypass: htmlBypass },
      "/training": { target: "http://localhost:8000", bypass: htmlBypass },
      "/odds": { target: "http://localhost:8000", bypass: htmlBypass },
      "/ai": { target: "http://localhost:8000", bypass: htmlBypass },
      "/system": { target: "http://localhost:8000", bypass: htmlBypass },
      "/fetch": { target: "http://localhost:8000", bypass: htmlBypass },
      "/subscription": { target: "http://localhost:8000", bypass: htmlBypass },
      "/audit": { target: "http://localhost:8000", bypass: htmlBypass },
      "/wallet": { target: "http://localhost:8000", bypass: htmlBypass },
      "/blockchain": { target: "http://localhost:8000", bypass: htmlBypass },
      "/marketplace": { target: "http://localhost:8000", bypass: htmlBypass },
      "/trust": { target: "http://localhost:8000", bypass: htmlBypass },
      "/bridge": { target: "http://localhost:8000", bypass: htmlBypass },
      "/developer": { target: "http://localhost:8000", bypass: htmlBypass },
      "/governance": { target: "http://localhost:8000", bypass: htmlBypass },
      "/notifications": { target: "http://localhost:8000", bypass: htmlBypass },
      "/pipeline": { target: "http://localhost:8000", bypass: htmlBypass },
      "/oracle": { target: "http://localhost:8000", bypass: htmlBypass },
      "/webhook": { target: "http://localhost:8000", bypass: htmlBypass },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
  preview: {
    port: 5000,
    host: "0.0.0.0",
    allowedHosts: true,
  },
});
