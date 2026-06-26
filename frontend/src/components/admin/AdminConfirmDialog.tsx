import React from "react";
import { AdminModal } from "./AdminModal";

interface AdminConfirmDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmLabel?: string;
  dangerous?: boolean;
  loading?: boolean;
}

export function AdminConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = "Confirm",
  dangerous = false,
  loading = false,
}: AdminConfirmDialogProps) {
  return (
    <AdminModal isOpen={isOpen} onClose={onClose} title={title} width="max-w-sm">
      <div className="flex flex-col gap-5">
        <p className="font-['Outfit'] text-sm text-white/70">{message}</p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="rounded-lg border border-white/10 px-4 py-2 font-['Outfit'] text-sm text-white/60 transition-colors hover:bg-white/10 disabled:opacity-40"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={`rounded-lg px-4 py-2 font-['Outfit'] text-sm font-semibold transition-colors disabled:opacity-40 ${
              dangerous
                ? "bg-red-600 text-white hover:bg-red-700"
                : "bg-[#00E676] text-black hover:bg-[#00c964]"
            }`}
          >
            {loading ? "Processing…" : confirmLabel}
          </button>
        </div>
      </div>
    </AdminModal>
  );
}
