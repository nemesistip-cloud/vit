declare global {
  interface Window {
    puter?: {
      ai: {
        chat: (
          message: string | { role: string; content: string }[],
          options?: { model?: string; stream?: boolean; temperature?: number }
        ) => Promise<{
          message: {
            content: string | { text: string }[];
          };
        }>;
      };
      auth: {
        isSignedIn: () => Promise<boolean>;
        signIn: () => Promise<void>;
        signOut: () => Promise<void>;
        getUser: () => Promise<{ username: string; uuid: string }>;
      };
    };
  }
}

export interface MatchAnalysis {
  home_prob: number;
  draw_prob: number;
  away_prob: number;
  confidence: number;
  reason: string;
  key_factors: string[];
  raw_content: string;
}

export const PUTER_CLAUDE_MODEL    = "claude-sonnet-4-6";
export const PUTER_GROK_MODEL      = "x-ai/grok-4.3";
export const PUTER_LLAMA_MODEL     = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo";
export const PUTER_MISTRAL_MODEL   = "mistral-large-latest";
export const PUTER_DEEPSEEK_MODEL  = "deepseek-chat";

export type PuterModel = "claude" | "grok" | "llama" | "mistral" | "deepseek";

const PUTER_MODEL_MAP: Record<PuterModel, string> = {
  claude:   PUTER_CLAUDE_MODEL,
  grok:     PUTER_GROK_MODEL,
  llama:    PUTER_LLAMA_MODEL,
  mistral:  PUTER_MISTRAL_MODEL,
  deepseek: PUTER_DEEPSEEK_MODEL,
};

export function puterModelId(model: PuterModel): string {
  return PUTER_MODEL_MAP[model] ?? PUTER_CLAUDE_MODEL;
}

export function isPuterAvailable(): boolean {
  return typeof window !== "undefined" && !!window.puter;
}

/**
 * Wait up to `timeoutMs` for the Puter.js CDN script to finish initialising.
 * The script tag in index.html loads it synchronously relative to DOMContentLoaded
 * but in production bundles the React app can mount before `window.puter` is set.
 */
export async function waitForPuter(timeoutMs = 5000): Promise<boolean> {
  if (isPuterAvailable()) return true;
  return new Promise((resolve) => {
    const deadline = Date.now() + timeoutMs;
    const check = () => {
      if (isPuterAvailable()) { resolve(true); return; }
      if (Date.now() >= deadline) { resolve(false); return; }
      setTimeout(check, 200);
    };
    check();
  });
}

export async function isPuterSignedIn(): Promise<boolean> {
  if (!isPuterAvailable()) return false;
  try {
    return await window.puter!.auth.isSignedIn();
  } catch {
    return false;
  }
}

export async function puterSignIn(): Promise<void> {
  if (!isPuterAvailable()) throw new Error("Puter.js not available");
  await window.puter!.auth.signIn();
}

export async function puterSignOut(): Promise<void> {
  if (!isPuterAvailable()) throw new Error("Puter.js not available");
  await window.puter!.auth.signOut();
}

export async function getPuterUser(): Promise<{ username: string; uuid: string } | null> {
  if (!isPuterAvailable()) return null;
  try {
    const signedIn = await window.puter!.auth.isSignedIn();
    if (!signedIn) return null;
    return await window.puter!.auth.getUser();
  } catch {
    return null;
  }
}

const SYSTEM_PROMPT =
  "You are an expert AI assistant for VIT (Value Intelligence Trust). " +
  "Help users understand the VIT ecosystem, including the VIT Intelligence layer, VIT Chain, programmable merit, and sports analytics. " +
  "Explain concepts like CLV, VITCoin, validators, and verifiable trust. " +
  "Be concise, visionary, and analytical.";

function extractText(content: string | { text: string }[]): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content) && content.length > 0) return content[0].text ?? "";
  return "";
}

function isRateLimitError(err: unknown): boolean {
  if (!err) return false;
  const msg = String((err as any)?.message || err).toLowerCase();
  return (
    msg.includes("rate limit") ||
    msg.includes("ratelimit") ||
    msg.includes("too many requests") ||
    msg.includes("429") ||
    msg.includes("quota") ||
    msg.includes("throttl")
  );
}

async function withRetry<T>(
  fn: () => Promise<T>,
  {
    maxAttempts = 3,
    baseDelayMs = 5000,
    label = "puter-ai",
  }: { maxAttempts?: number; baseDelayMs?: number; label?: string } = {}
): Promise<T> {
  let lastErr: unknown;
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (err) {
      lastErr = err;
      if (isRateLimitError(err)) {
        const delayMs = baseDelayMs * Math.pow(2, attempt - 1) + Math.random() * 1000;
        console.warn(`[${label}] rate-limit hit (attempt ${attempt}/${maxAttempts}) — retrying in ${Math.round(delayMs / 1000)}s`);
        if (attempt < maxAttempts) {
          await new Promise((r) => setTimeout(r, delayMs));
          continue;
        }
        throw new Error(`Rate limit exceeded after ${maxAttempts} attempts. Please wait a minute or switch Puter accounts.`);
      }
      throw err;
    }
  }
  throw lastErr;
}

export async function puterChat(
  message: string,
  history: { role: string; content: string }[] = [],
  model: PuterModel = "claude"
): Promise<string> {
  if (!isPuterAvailable()) throw new Error("Puter not available");

  const modelId = puterModelId(model);

  const messages: { role: string; content: string }[] = [
    { role: "system", content: SYSTEM_PROMPT },
    ...history.map((t) => ({ role: t.role, content: t.content })),
    { role: "user", content: message },
  ];

  const response = await withRetry(
    () => window.puter!.ai.chat(messages, { model: modelId }),
    { label: `puter-chat-${model}`, maxAttempts: 3, baseDelayMs: 8000 }
  );

  return extractText(response.message.content);
}

const MATCH_ANALYSIS_SYSTEM =
  "You are a sharp professional football betting analyst with deep expertise in statistical modelling, " +
  "team form cycles, squad availability, tactical matchups, and market efficiency. " +
  "You provide precise, evidence-based probability estimates. " +
  "CRITICAL: You MUST respond with ONLY a raw JSON object — no markdown, no code fences, no explanations outside the JSON.";

function buildMatchPrompt(
  home: string,
  away: string,
  league: string,
  priorHome: number,
  priorDraw: number,
  priorAway: number
): string {
  return (
    `Analyze this football match and provide your independent probability assessment.\n\n` +
    `Match: ${home} vs ${away}\n` +
    `League: ${league}\n` +
    `ML Ensemble Prior: Home ${(priorHome * 100).toFixed(1)}% | Draw ${(priorDraw * 100).toFixed(1)}% | Away ${(priorAway * 100).toFixed(1)}%\n\n` +
    `Provide your INDEPENDENT analysis as a raw JSON object (no markdown, no code fences):\n` +
    `{\n` +
    `  "home_prob": 0.00,\n` +
    `  "draw_prob": 0.00,\n` +
    `  "away_prob": 0.00,\n` +
    `  "confidence": 0.00,\n` +
    `  "reason": "one-line tactical summary (max 120 chars)",\n` +
    `  "key_factors": ["factor 1", "factor 2", "factor 3"]\n` +
    `}\n\n` +
    `Rules:\n` +
    `- home_prob + draw_prob + away_prob MUST equal exactly 1.0\n` +
    `- confidence: 0.5 = uncertain, 0.65 = moderate, 0.80 = high conviction\n` +
    `- reason: concise tactical reasoning, no filler phrases\n` +
    `- key_factors: 2-4 decisive factors (injuries, form, h2h, tactics)\n` +
    `- Return ONLY the JSON object, nothing else`
  );
}

function parseJsonSafe(raw: string): any {
  let text = raw.trim();
  const fenceMatch = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenceMatch) text = fenceMatch[1].trim();
  const objMatch = text.match(/\{[\s\S]*\}/);
  if (objMatch) text = objMatch[0];
  return JSON.parse(text);
}

export async function analyzeMatchWithPuter(
  homeTeam: string,
  awayTeam: string,
  league: string,
  priorHome = 0.34,
  priorDraw = 0.33,
  priorAway = 0.33,
  model: PuterModel = "claude"
): Promise<MatchAnalysis> {
  if (!isPuterAvailable()) throw new Error("Puter.js not available — ensure you are signed in");

  const modelId = puterModelId(model);
  const prompt = buildMatchPrompt(homeTeam, awayTeam, league, priorHome, priorDraw, priorAway);

  const messages: { role: string; content: string }[] = [
    { role: "system", content: MATCH_ANALYSIS_SYSTEM },
    { role: "user", content: prompt },
  ];

  const response = await withRetry(
    () => window.puter!.ai.chat(messages, { model: modelId, temperature: 0.2 } as any),
    { label: `puter-analyze-${model}`, maxAttempts: 4, baseDelayMs: 10000 }
  );

  const raw = extractText(response.message.content);

  let parsed: any;
  try {
    parsed = parseJsonSafe(raw);
  } catch {
    throw new Error(`AI returned non-parseable response: ${raw.slice(0, 120)}`);
  }

  const h = Math.max(0, parseFloat(parsed.home_prob) || priorHome);
  const d = Math.max(0, parseFloat(parsed.draw_prob) || priorDraw);
  const a = Math.max(0, parseFloat(parsed.away_prob) || priorAway);
  const total = h + d + a || 1;

  return {
    home_prob: parseFloat((h / total).toFixed(4)),
    draw_prob: parseFloat((d / total).toFixed(4)),
    away_prob: parseFloat((a / total).toFixed(4)),
    confidence: Math.min(1, Math.max(0.3, parseFloat(parsed.confidence) || 0.65)),
    reason: String(parsed.reason || "AI match analysis").slice(0, 500),
    key_factors: Array.isArray(parsed.key_factors) ? parsed.key_factors.slice(0, 5) : [],
    raw_content: raw,
  };
}
