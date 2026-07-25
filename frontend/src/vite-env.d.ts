/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GATEWAY_URL?: string
  readonly VITE_AI_URL?: string
  readonly VITE_STORAGE_URL?: string
  readonly VITE_CHAIN_URL?: string
  readonly VITE_GITHUB_OWNER?: string
  readonly VITE_GITHUB_REPO?: string
  readonly VITE_GITHUB_PAT?: string
  readonly VITE_RENDER_API_KEY?: string
  readonly VITE_SESSION_SECRET?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
