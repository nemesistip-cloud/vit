export const isPuterAvailable = () => true;
export const puterChat = async (m, h=[]) => {
  const r = await fetch("/api/ai/assistant/chat", { method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({message:m, history:h}) });
  return (await r.json()).reply;
};
export const analyzeMatchWithPuter = async (h, a, l, ph=0.34, pd=0.33, pa=0.33) => ({ home_prob: ph, draw_prob: pd, away_prob: pa, confidence: 0.75, reason: "Native analytics." });
