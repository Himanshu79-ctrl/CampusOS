import React from "react";
import { Link } from "react-router-dom";
import { Inbox, ArrowRight } from "lucide-react";

export const EmptyState = ({
  icon: Icon = Inbox,
  title = "No data available",
  description = "There are no records found for this section yet.",
  actionLabel,
  onAction,
  actionLink,
  className = "",
}) => {
  return (
    <div
      className={`bg-white rounded-2xl border border-dashed border-slate-200 p-8 sm:p-12 text-center flex flex-col items-center justify-center max-w-xl mx-auto my-6 ${className}`}
    >
      <div className="w-13 h-13 rounded-2xl bg-slate-50 border border-slate-100 flex items-center justify-center text-slate-400 mb-4 shadow-2xs">
        <Icon className="w-6 h-6" />
      </div>

      <h3 className="text-base font-bold text-slate-800">{title}</h3>
      <p className="text-xs sm:text-sm text-slate-500 mt-1.5 max-w-md leading-relaxed">
        {description}
      </p>

      {(actionLabel && (onAction || actionLink)) && (
        <div className="mt-5">
          {actionLink ? (
            <Link
              to={actionLink}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors"
            >
              <span>{actionLabel}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          ) : (
            <button
              onClick={onAction}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
            >
              <span>{actionLabel}</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default EmptyState;
