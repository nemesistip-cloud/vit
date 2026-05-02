declare global {
  interface Window {
    puter?: {
      ai: {
        chat: (
          message: string | { role: string; content: string }[],
          options?: { model?: string; stream?: boolean }
        ) => Promise<{ message: { content: { text: string }[] } }>;
      };
      auth: {
        isSignedIn: () => Promise<boolean>;
        signIn: () => Promise<void>;
      };
    };
  }
}

export const PUTER_MODEL = "claude-sonnet-4-6";

export function isPuterAvailable(): boolean {
  return typeof window !== "undefined" && !!window.puter;
}

export async function puterChat(
  message: string,
  history: { role: string; content: string }[] = []
): Promise<string> {
  if (!isPuterAvailable()) throw new Error("Puter not available");

  const messages: { role: string; content: string }[] = [
    {
      role: "system",
      content:
        "You are an expert AI assistant for the VIT Sports Intelligence Network — a professional football prediction and betting analytics platform. Help users understand predictions, AI models, CLV (Closing Line Value), the wallet, VITCoin, validators, blockchain consensus, and all platform features. Be concise, insightful, and analytical. Use sports analytics terminology confidently.",
    },
    ...history.map((t) => ({ role: t.role, content: t.content })),
    { role: "user", content: message },
  ];

  const response = await window.puter!.ai.chat(messages, {
    model: PUTER_MODEL,
  });

  return response.message.content[0].text;
}
