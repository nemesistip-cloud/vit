import React, { useState } from "react";

export const CURRENCIES = [
  { value: "VITCoin", label: "VITCoin", symbol: "VIT", flag: "🔮" },
  { value: "NGN", label: "Naira", symbol: "₦", flag: "🇳🇬" },
  { value: "USD", label: "USD", symbol: "$", flag: "🇺🇸" },
  { value: "USDT", label: "USDT", symbol: "₮", flag: "💵" },
  { value: "PI", label: "Pi", symbol: "π", flag: "π" },
] as const;

export type CurrencyOption = (typeof CURRENCIES)[number]["value"];

interface CurrencySelectorProps {
  value: CurrencyOption;
  onChange: (v: CurrencyOption) => void;
  exclude?: CurrencyOption[];
  label?: string;
  disabled?: boolean;
}

export function CurrencySelector({
  value,
  onChange,
  exclude = [],
  label,
  disabled = false,
}: CurrencySelectorProps) {
  const [open, setOpen] = useState(false);
  const options = CURRENCIES.filter((c) => !exclude.includes(c.value));
  const selected = CURRENCIES.find((c) => c.value === value) ?? CURRENCIES[0];

  return (
    <div className="relative">
      {label && (
        <label className="block text-[10px] uppercase tracking-widest text-white/40 font-['Outfit'] mb-1">
          {label}
        </label>
      )}
      <button
        type="button"
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        className={`
          flex items-center gap-2 rounded-lg border border-white/[0.08] bg-white/[0.03]
          px-3 py-2 w-full transition-colors hover:border-[#00E676]/30
          ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
        `}
      >
        <span className="text-base leading-none">{selected.flag}</span>
        <span className="text-sm text-white font-['Outfit'] flex-1 text-left">{selected.label}</span>
        <span className="text-[10px] text-white/30 font-['JetBrains_Mono'] uppercase">{selected.symbol}</span>
        {!disabled && (
          <svg
            className={`w-3 h-3 text-white/30 transition-transform ${open ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </button>

      {open && (
        <div className="absolute z-50 top-full mt-1 w-full rounded-lg border border-white/[0.08] bg-[#0d1117] shadow-xl overflow-hidden">
          {options.map((opt) => (
            <button
              key={opt.value}
              type="button"
              onClick={() => {
                onChange(opt.value);
                setOpen(false);
              }}
              className={`
                flex items-center gap-2 w-full px-3 py-2.5 text-left transition-colors
                hover:bg-white/[0.04]
                ${opt.value === value ? "bg-[#00E676]/5 text-[#00E676]" : "text-white"}
              `}
            >
              <span>{opt.flag}</span>
              <span className="text-sm font-['Outfit'] flex-1">{opt.label}</span>
              <span className="text-[10px] text-white/30 font-['JetBrains_Mono'] uppercase">{opt.symbol}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
