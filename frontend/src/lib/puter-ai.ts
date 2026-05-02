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
      };
    };
  }
}

export const PUTER_CLAUDE_MODEL = "claude-sonnet-4-6";
export const PUTER_GROK_MODEL   = "x-ai/grok-4.3";

export type PuterModel = "claude" | "grok";

export function isPuterAvailable(): boolean {
  return typeof window !== "undefined" && !!window.puter;
}

const SYSTEM_PROMPT =
  "You are an expert AI assistant for the VIT Sports Intelligence Network — a professional football prediction and betting analytics platform. " +
  "Help users understand predictions, AI models, CLV (Closing Line Value), the wallet, VITCoin, validators, blockchain consensus, and all platform features. " +
  "Be concise, insightful, and analytical. Use sports analytics terminology confidently.";

function extractText(content: string | { text: string }[]): string {
  if (typeof content === "string") return content;
  if (Array.isArray(content) && content.length > 0) return content[0].text ?? "";
  return "";
}

export async function puterChat(
  message: string,
  history: { role: string; content: string }[] = [],
  model: PuterModel = "claude"
): Promise<string> {
  if (!isPuterAvailable()) throw new Error("Puter not available");

  const modelId = model === "grok" ? PUTER_GROK_MODEL : PUTER_CLAUDE_MODEL;

  const messages: { role: string; content: string }[] = [
    { role: "system", content: SYSTEM_PROMPT },
    ...history.map((t) => ({ role: t.role, content: t.content })),
    { role: "user", content: message },
  ];

  const response = await window.puter!.ai.chat(messages, { model: modelId });

  return extractText(response.message.content);
}
