import React from "react";

interface AmountInputProps {
  value: string;
  onChange: (v: string) => void;
  label?: string;
  placeholder?: string;
  max?: number;
  min?: number;
  disabled?: boolean;
  suffix?: string;
  error?: string;
  hint?: string;
}

export function AmountInput({
  value,
  onChange,
  label,
  placeholder = "0.00",
  max,
  min,
  disabled = false,
  suffix,
  error,
  hint,
}: AmountInputProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const v = e.target.value;
    if (v === "" || /^\d*\.?\d*$/.test(v)) {
      onChange(v);
    }
  };

  const setMax = () => {
    if (max !== undefined) onChange(max.toString());
  };

  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label className="text-[10px] uppercase tracking-widest text-white/40 font-['Outfit']">
          {label}
        </label>
      )}
      <div
        className={`
          flex items-center gap-2 rounded-lg border px-3 py-2 bg-white/[0.03]
          transition-colors focus-within:border-[#00E676]/40
          ${error ? "border-red-500/50" : "border-white/[0.08]"}
          ${disabled ? "opacity-50 cursor-not-allowed" : ""}
        `}
      >
        <input
          type="text"
          inputMode="decimal"
          value={value}
          onChange={handleChange}
          placeholder={placeholder}
          disabled={disabled}
          className={`
            flex-1 bg-transparent text-white font-['JetBrains_Mono'] text-base
            outline-none placeholder:text-white/20 min-w-0
            ${disabled ? "cursor-not-allowed" : ""}
          `}
        />
        {suffix && (
          <span className="text-xs text-white/40 font-['Outfit'] uppercase shrink-0">{suffix}</span>
        )}
        {max !== undefined && !disabled && (
          <button
            type="button"
            onClick={setMax}
            className="text-[10px] text-[#00E676]/70 font-['Outfit'] uppercase tracking-widest hover:text-[#00E676] transition-colors shrink-0"
          >
            MAX
          </button>
        )}
      </div>
      {hint && !error && (
        <p className="text-[10px] text-white/30 font-['Outfit']">{hint}</p>
      )}
      {error && (
        <p className="text-[10px] text-red-400 font-['Outfit']">{error}</p>
      )}
    </div>
  );
}
