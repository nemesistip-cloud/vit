/**
 * VIT Mobile Money & Offline Fallback
 * Optimized for Nigerian and Pan-African payment ecosystems
 */

export const MOBILE_MONEY_PROVIDERS = [
  { id: "opay", name: "OPay", region: "NG", icon: "opay-logo" },
  { id: "palmpay", name: "PalmPay", region: "NG", icon: "palmpay-logo" },
  { id: "mtn-momo", name: "MTN MoMo", region: "GH/NG/UG", icon: "momo-logo" },
];

export function generateUSSDString(amount: number, reference: string) {
  // Example USSD for a hypothetical VIT bank partner
  return `*555*1*${amount}*${reference}#`;
}

export function triggerSMSFallback(type: string, payload: any) {
  const body = `VIT:${type}:${JSON.stringify(payload)}`;
  window.location.href = `sms:+234000000000?body=${encodeURIComponent(body)}`;
}
