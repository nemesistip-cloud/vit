/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_GATEWAY_URL: string
  readonly VITE_AI_URL: string
  readonly VITE_STORAGE_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
