import React from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

export const StatCard = ({
  title,
  value,
  subtext,
  icon: Icon,
  iconColor = "text-indigo-600",
  iconBg = "bg-indigo-50 border-indigo-100",
  trend,
  trendType = "neutral",
  isLoading = false,
}) => {
  if (isLoading) {
    return (
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs animate-pulse">
        <div className="flex items-center justify-between">
          <div className="h-4 w-24 bg-slate-200 rounded" />
          <div className="w-10 h-10 rounded-xl bg-slate-200" />
        </div>
        <div className="mt-4 space-y-2">
          <div className="h-7 w-20 bg-slate-200 rounded" />
          <div className="h-3 w-32 bg-slate-100 rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs hover:shadow-md transition-all duration-200 flex flex-col justify-between">
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider block">
            {title}
          </span>
          <div className="mt-1 flex items-baseline gap-2">
            <span className="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight font-sans">
              {value ?? "—"}
            </span>
            {trend && (
              <span
                className={`inline-flex items-center text-xs font-semibold ${
                  trendType === "up"
                    ? "text-emerald-600"
                    : trendType === "down"
                    ? "text-rose-600"
                    : "text-slate-500"
                }`}
              >
                {trendType === "up" && <TrendingUp className="w-3.5 h-3.5 mr-0.5" />}
                {trendType === "down" && <TrendingDown className="w-3.5 h-3.5 mr-0.5" />}
                {trendType === "neutral" && <Minus className="w-3.5 h-3.5 mr-0.5" />}
                {trend}
              </span>
            )}
          </div>
        </div>

        {Icon && (
          <div
            className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 border ${iconBg} ${iconColor}`}
          >
            <Icon className="w-5 h-5" />
          </div>
        )}
      </div>

      {subtext && (
        <p className="mt-3 text-xs text-slate-500 font-medium border-t border-slate-100 pt-2.5">
          {subtext}
        </p>
      )}
    </div>
  );
};

export default StatCard;
