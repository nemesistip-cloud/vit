import React from "react";

export interface Column<T = any> {
  key: string;
  label: string;
  render?: (value: any, row: T) => React.ReactNode;
  sortable?: boolean;
}

export interface PaginationProps {
  page: number;
  total: number;
  limit: number;
  onChange: (page: number) => void;
}

interface AdminTableProps<T = any> {
  columns: Column<T>[];
  data: T[];
  onRowClick?: (row: T) => void;
  loading: boolean;
  pagination: PaginationProps;
  emptyMessage?: string;
}

export function AdminTable<T extends Record<string, any>>({
  columns,
  data,
  onRowClick,
  loading,
  pagination,
  emptyMessage = "No records found",
}: AdminTableProps<T>) {
  const totalPages = Math.ceil(pagination.total / pagination.limit);

  return (
    <div className="flex flex-col gap-2">
      <div className="overflow-x-auto rounded-lg border border-white/10">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-white/10 bg-white/5">
              {columns.map((col) => (
                <th
                  key={col.key}
                  className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-white/50"
                >
                  {col.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center">
                  <div className="flex items-center justify-center gap-2 text-white/40">
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-[#00E676]/30 border-t-[#00E676]" />
                    <span className="font-['Outfit'] text-xs uppercase tracking-widest">Loading…</span>
                  </div>
                </td>
              </tr>
            ) : data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center font-['Outfit'] text-sm text-white/30">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row, idx) => (
                <tr
                  key={idx}
                  onClick={() => onRowClick?.(row)}
                  className={`border-b border-white/5 transition-colors ${
                    onRowClick ? "cursor-pointer hover:bg-white/5" : ""
                  }`}
                >
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3 text-white/80">
                      {col.render
                        ? col.render(row[col.key], row)
                        : String(row[col.key] ?? "—")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between px-1 py-1">
          <span className="font-['JetBrains_Mono'] text-xs text-white/40">
            {pagination.total} total · page {pagination.page} of {totalPages}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => pagination.onChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="rounded px-3 py-1 text-xs text-white/60 hover:bg-white/10 disabled:opacity-30"
            >
              ← Prev
            </button>
            {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
              const p = Math.max(1, Math.min(totalPages - 4, pagination.page - 2)) + i;
              return p <= totalPages ? (
                <button
                  key={p}
                  onClick={() => pagination.onChange(p)}
                  className={`rounded px-3 py-1 font-['JetBrains_Mono'] text-xs ${
                    p === pagination.page
                      ? "bg-[#00E676]/20 text-[#00E676]"
                      : "text-white/60 hover:bg-white/10"
                  }`}
                >
                  {p}
                </button>
              ) : null;
            })}
            <button
              onClick={() => pagination.onChange(pagination.page + 1)}
              disabled={pagination.page >= totalPages}
              className="rounded px-3 py-1 text-xs text-white/60 hover:bg-white/10 disabled:opacity-30"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
