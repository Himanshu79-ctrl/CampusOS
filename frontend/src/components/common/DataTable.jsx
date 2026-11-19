import React from "react";
import { EmptyState } from "./EmptyState";
import { Loader2 } from "lucide-react";

export const DataTable = ({
  columns = [],
  data = [],
  isLoading = false,
  emptyTitle = "No records found",
  emptyMessage = "No matching records are available.",
  keyField = "id",
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-2xs">
        <div className="p-12 flex flex-col items-center justify-center">
          <Loader2 className="w-6 h-6 animate-spin text-indigo-600 mb-2" />
          <span className="text-xs text-slate-500 font-medium">Loading records...</span>
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-2xs">
        <EmptyState title={emptyTitle} description={emptyMessage} className="border-none shadow-none" />
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-2xs">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              {columns.map((col, idx) => (
                <th
                  key={idx}
                  className={`px-4 py-3.5 ${col.className || ""}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {data.map((row, rowIdx) => (
              <tr
                key={row[keyField] ?? rowIdx}
                className="hover:bg-slate-50/70 transition-colors"
              >
                {columns.map((col, colIdx) => {
                  let content;
                  if (typeof col.accessor === "function") {
                    content = col.accessor(row);
                  } else if (typeof col.accessor === "string") {
                    content = row[col.accessor];
                  } else {
                    content = null;
                  }

                  return (
                    <td
                      key={colIdx}
                      className={`px-4 py-3 text-slate-700 ${col.className || ""}`}
                    >
                      {content ?? "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default DataTable;
